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
from app.cardapios import carregar_trechos
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
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # o terminal do Windows usa cp1252 e não imprime ✓/✗
    load_dotenv()
    casos = json.loads((PASTA / "perguntas.json").read_text(encoding="utf-8"))
    indice = Indice(carregar_trechos(), *embedder_e5())
    llm = None
    if not args.so_busca:
        from app.llm import Gemini
        llm = Gemini()
        print(f"Modelo: {llm.nome}")

    resultados = []
    for n, caso in enumerate(casos, 1):
        recuperados = [t.id for t, _ in indice.buscar(caso["pergunta"], k=args.k)]
        linha = {"pergunta": caso["pergunta"], "tipo": caso["tipo"], "recuperados": recuperados}
        if not caso.get("fora_do_escopo"):
            achou = [f for f in caso["fontes"] if f in recuperados]
            linha["busca_ok"] = len(achou) == len(caso["fontes"])
            linha["busca_recall"] = len(achou) / len(caso["fontes"])
        if llm:
            if n > 1:
                time.sleep(args.pausa)
            r = responder(caso["pergunta"], indice, llm, k=args.k)
            fontes = [t.id for t in r.fontes]
            linha |= {"resposta": r.resposta, "fontes_citadas": fontes, **avaliar_resposta(caso, r.resposta, fontes)}
            linha["ok"] = linha["resposta_ok"] and linha["citacao_ok"]
        resultados.append(linha)
        marca = "✓" if linha.get("ok", linha.get("busca_ok", True)) else "✗"
        print(f"{marca} {n:2}/{len(casos)} {caso['pergunta']}")

    (PASTA / ("resultados_busca.json" if args.so_busca else "resultados.json")).write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    relatorio = gerar_relatorio(resultados, args.k, llm.nome if llm else None)
    (PASTA / ("relatorio_busca.md" if args.so_busca else "relatorio.md")).write_text(relatorio, encoding="utf-8")
    print("\n" + relatorio)


def gerar_relatorio(resultados: list[dict], k: int, modelo: str | None) -> str:
    no_escopo = [r for r in resultados if "busca_ok" in r]
    recall_medio = sum(r["busca_recall"] for r in no_escopo) / len(no_escopo)
    linhas = [
        "# Relatório de avaliação",
        "",
        f"{date.today():%d/%m/%Y} · {len(resultados)} perguntas · k = {k}" + (f" · modelo `{modelo}`" if modelo else ""),
        "",
        "| Métrica | Resultado |",
        "|---|---|",
        f"| Busca: todos os trechos esperados no top {k} | {pct([r['busca_ok'] for r in no_escopo])} |",
        f"| Busca: recall médio | {100 * recall_medio:.0f}% |",
    ]
    if modelo:
        linhas += [
            f"| Resposta correta | {pct([r['resposta_ok'] for r in resultados])} |",
            f"| Fonte citada corretamente | {pct([r['citacao_ok'] for r in resultados])} |",
            f"| **Aprovada (resposta + fonte)** | **{pct([r['ok'] for r in resultados])}** |",
        ]
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
        if not r.get("busca_ok", True):
            linhas.append(f"- Busca não trouxe todos os trechos esperados. Recuperados: {', '.join(r['recuperados'])}")
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
