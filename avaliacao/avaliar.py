"""Mede a qualidade do RAG num conjunto de perguntas com resposta conhecida.

    python -m avaliacao.avaliar             # busca + Gemini (precisa de GEMINI_API_KEY no .env)
    python -m avaliacao.avaliar --so-busca  # só a busca: grátis, sem internet além do modelo de embeddings

Duas camadas, avaliadas separadamente, porque falham por motivos diferentes:
- Busca: os trechos certos estão entre os k recuperados? Se não estão, o LLM nem tem como acertar.
- Resposta: o texto contém os fatos esperados, não contém os proibidos e cita uma fonte correta?
  Para perguntas fora do escopo, o certo é recusar com a frase padrão.
A checagem da resposta é por palavras-chave (determinística e auditável), não por outro LLM.
"""
import argparse
import json
import os
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from app.busca import Indice, embedder_e5
from app import agente
from app.cardapios import carregar_trechos
from app.catalogo import carregar_catalogo
from app.ferramentas import Ferramentas
from app.llm import MODELO_AVALIADO, CotaDiariaEsgotada, ErroLLM
from app.rag import responder

PASTA = Path(__file__).resolve().parent


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def avaliar_resposta(caso: dict, resposta: str, fontes: list[str]) -> dict:
    texto = normalizar(resposta)
    if caso.get("fora_do_escopo"):
        recusou = "nao encontrei" in texto
        return {"resposta_ok": recusou, "citacao_ok": not fontes, "faltou": [] if recusou else ["recusa"], "proibido": []}
    faltou = [grupo[0] for grupo in caso["deve_conter"] if not any(normalizar(op) in texto for op in grupo)]
    proibido = [p for p in caso.get("nao_deve_conter", []) if normalizar(p) in texto]
    return {
        "resposta_ok": not faltou and not proibido,
        "citacao_ok": bool(set(fontes) & set(caso["fontes"])),
        "faltou": faltou,
        "proibido": proibido,
    }


def pct(valores: list[bool]) -> str:
    return f"{100 * sum(valores) / len(valores):.0f}% ({sum(valores)}/{len(valores)})" if valores else "—"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--so-busca", action="store_true", help="avalia só a busca, sem chamar o Gemini")
    parser.add_argument("-k", type=int, default=8)
    parser.add_argument("--pausa", type=float, default=float(os.environ.get("AVAL_PAUSA", 4)),
                        help="segundos entre chamadas ao Gemini (limite da camada gratuita)")
    parser.add_argument("--modo", choices=["rag", "agente"], default="rag",
                        help="rag: busca + uma chamada ao LLM; agente: o LLM chama ferramentas")
    parser.add_argument("--conjunto", choices=["principal", "agregacao"], default="principal",
                        help="principal: 30 perguntas variadas; agregacao: 'mais barato', 'todos os', 'quantos'")
    parser.add_argument("--recalcular", action="store_true",
                        help="reavalia as respostas já salvas com o gabarito atual, sem chamar o Gemini")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # o terminal do Windows usa cp1252 e não imprime ✓/✗
    load_dotenv()
    arquivo = "perguntas.json" if args.conjunto == "principal" else "perguntas_agregacao.json"
    casos = json.loads((PASTA / arquivo).read_text(encoding="utf-8"))
    # rag + principal mantém os nomes originais; as outras combinações ganham sufixo
    sufixo = "_busca" if args.so_busca else ("" if (args.modo, args.conjunto) == ("rag", "principal")
                                             else f"_{args.modo}_{args.conjunto}")

    if args.recalcular:
        salvos = json.loads((PASTA / f"resultados{sufixo}.json").read_text(encoding="utf-8"))
        modelo = recalcular(salvos, casos)
        (PASTA / f"resultados{sufixo}.json").write_text(json.dumps(salvos, ensure_ascii=False, indent=2), encoding="utf-8")
        relatorio = gerar_relatorio(salvos, args.k, modelo, args.modo, args.conjunto)
        (PASTA / f"relatorio{sufixo}.md").write_text(relatorio, encoding="utf-8")
        print(relatorio)
        return

    indice = Indice(carregar_trechos(), *embedder_e5())
    ferramentas = Ferramentas(*carregar_catalogo(), indice) if args.modo == "agente" else None
    llm = None
    if not args.so_busca:
        from app.llm import Gemini
        llm = Gemini()
        print(f"Modelo: {llm.nome} · modo: {args.modo} · conjunto: {args.conjunto}")

    def avaliar_caso(n: int, caso: dict) -> dict:
        recuperados = [t.id for t, _ in indice.buscar(caso["pergunta"], k=args.k)]
        linha = {"pergunta": caso["pergunta"], "tipo": caso["tipo"], "recuperados": recuperados}
        if not caso.get("fora_do_escopo"):
            achou = [f for f in caso["fontes"] if f in recuperados]
            linha["busca_ok"] = len(achou) == len(caso["fontes"])
            linha["busca_recall"] = len(achou) / len(caso["fontes"])
        if not llm:
            return linha
        inicio = time.perf_counter()
        try:
            if ferramentas:
                r = agente.responder(caso["pergunta"], ferramentas, llm)
                texto, fontes = r.resposta, r.fontes
                linha["passos"] = agente.resumo_passos(r.passos)
            else:
                r = responder(caso["pergunta"], indice, llm, k=args.k)
                texto, fontes = r.resposta, [t.id for t in r.fontes]
        except CotaDiariaEsgotada as erro:
            sys.exit(f"\nAvaliação interrompida na pergunta {n}: {erro}\nNenhum relatório foi gravado; rode de novo amanhã ou com outro modelo.")
        except ErroLLM as erro:  # uma pergunta com erro conta como falha, sem derrubar a avaliação inteira
            texto, fontes = f"[ERRO] {erro}", []
        linha |= {"resposta": texto, "fontes_citadas": fontes, "segundos": round(time.perf_counter() - inicio, 2),
                  **avaliar_resposta(caso, texto, fontes)}
        linha["ok"] = linha["resposta_ok"] and linha["citacao_ok"]
        return linha

    def mostrar(n: int, linha: dict) -> None:
        marca = "✓" if linha.get("ok", linha.get("busca_ok", True)) else "✗"
        print(f"{marca} {n:2}/{len(casos)} {linha['pergunta']}")

    resultados = []
    for n, caso in enumerate(casos, 1):
        if llm and n > 1:
            time.sleep(args.pausa)
        resultados.append(avaliar_caso(n, caso))
        mostrar(n, resultados[-1])

    # Erro do Gemini (sobrecarga, timeout) é infraestrutura, não qualidade: refaz essas perguntas no final
    refeitas = 0
    for rodada in range(2):
        com_erro = [i for i, r in enumerate(resultados) if r.get("resposta", "").startswith("[ERRO]")]
        if not com_erro:
            break
        print(f"\n{len(com_erro)} pergunta(s) com erro do Gemini; refazendo em 60 s (rodada {rodada + 1}/2)...")
        time.sleep(60)
        for i in com_erro:
            resultados[i] = avaliar_caso(i + 1, casos[i])
            resultados[i]["refeita"] = True
            refeitas += 1
            mostrar(i + 1, resultados[i])
            time.sleep(args.pausa)
    if refeitas:
        print(f"{refeitas} nova(s) tentativa(s) por erro do Gemini.")

    (PASTA / f"resultados{sufixo}.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    relatorio = gerar_relatorio(resultados, args.k, llm.nome if llm else None, args.modo, args.conjunto)
    (PASTA / f"relatorio{sufixo}.md").write_text(relatorio, encoding="utf-8")
    print("\n" + relatorio)


def recalcular(salvos: list[dict], casos: list[dict]) -> str:
    """Reaplica a checagem às respostas salvas (ex.: depois de corrigir um erro no gabarito). Devolve o modelo usado."""
    por_pergunta = {c["pergunta"]: c for c in casos}
    for linha in salvos:
        caso = por_pergunta[linha["pergunta"]]
        if "fontes" in caso and "recuperados" in linha:
            achou = [f for f in caso["fontes"] if f in linha["recuperados"]]
            linha["busca_ok"] = len(achou) == len(caso["fontes"])
            linha["busca_recall"] = len(achou) / len(caso["fontes"])
        linha |= avaliar_resposta(caso, linha["resposta"], linha["fontes_citadas"])
        linha["ok"] = linha["resposta_ok"] and linha["citacao_ok"]
    return os.environ.get("GEMINI_MODEL") or MODELO_AVALIADO


def gerar_relatorio(resultados: list[dict], k: int, modelo: str | None, modo: str = "rag", conjunto: str = "principal") -> str:
    no_escopo = [r for r in resultados if "busca_ok" in r]
    recall_medio = sum(r["busca_recall"] for r in no_escopo) / len(no_escopo)
    linhas = [
        "# Relatório de avaliação",
        "",
        f"{date.today():%d/%m/%Y} · conjunto **{conjunto}** · {len(resultados)} perguntas · "
        + (f"modo **{modo}** · modelo `{modelo}`" if modelo else f"só busca, k = {k}"),
        "",
        "| Métrica | Resultado |",
        "|---|---|",
    ]
    if modo == "rag":  # no agente, a busca de k trechos fixos não existe: ele escolhe o que consultar
        linhas += [
            f"| Busca: todos os trechos esperados no top {k} | {pct([r['busca_ok'] for r in no_escopo])} |",
            f"| Busca: recall médio | {100 * recall_medio:.0f}% |",
        ]
    if modelo:
        linhas += [
            f"| Resposta correta | {pct([r['resposta_ok'] for r in resultados])} |",
            f"| Fonte citada corretamente | {pct([r['citacao_ok'] for r in resultados])} |",
            f"| **Aprovada (resposta + fonte)** | **{pct([r['ok'] for r in resultados])}** |",
        ]
        tempos = sorted(r["segundos"] for r in resultados)
        linhas.append(f"| Tempo de resposta (mediana · pior) | {tempos[len(tempos) // 2]:.1f} s · {tempos[-1]:.1f} s |")
        refeitas = sum(1 for r in resultados if r.get("refeita"))
        erros = sum(1 for r in resultados if r["resposta"].startswith("[ERRO]"))
        linhas.append(f"| Refeitas por erro do Gemini · ainda com erro | {refeitas} · {erros} |")
    por_tipo = defaultdict(list)
    for r in resultados:
        por_tipo[r["tipo"]].append(r)
    chave = "ok" if modelo else "busca_ok"
    linhas += ["", "## Por tipo de pergunta", "", "| Tipo | Aprovadas |", "|---|---|"]
    linhas += [f"| {tipo} | {pct([r.get(chave, True) for r in rs])} |" for tipo, rs in por_tipo.items()]

    falhas = [r for r in resultados if not r.get(chave, True)]
    linhas += ["", f"## Falhas ({len(falhas)})", ""]
    for r in falhas:
        linhas.append(f"**{r['pergunta']}** ({r['tipo']})")
        if modo == "rag" and not r.get("busca_ok", True):
            linhas.append(f"- Busca não trouxe todos os trechos esperados. Recuperados: {', '.join(r['recuperados'])}")
        if "passos" in r:
            linhas.append(f"- Ferramentas: {r['passos']}")
        if modelo:
            linhas.append(f"- Resposta: {r['resposta']}")
            if r["faltou"]:
                linhas.append(f"- Faltou: {', '.join(r['faltou'])}")
            if r["proibido"]:
                linhas.append(f"- Continha o proibido: {', '.join(r['proibido'])}")
            if not r["citacao_ok"]:
                linhas.append(f"- Fontes citadas: {', '.join(r['fontes_citadas']) or 'nenhuma'}")
        linhas.append("")
    return "\n".join(linhas)


if __name__ == "__main__":
    main()
