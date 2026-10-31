"""Gera avaliacao/perguntas_agregacao.json calculando as respostas esperadas a partir dos próprios cardápios.

Escrever "o mais barato" à mão é fácil de errar (ou de ficar velho quando um cardápio muda); aqui o
gabarito sai do mesmo catálogo que o agente consulta.

    python -m avaliacao.gerar_agregacao
"""
import json
from pathlib import Path

from app.catalogo import carregar_catalogo, filtrar

pratos, restaurantes = carregar_catalogo()
info = {r.nome: r for r in restaurantes}


def ids(lista):
    return [p.id for p in lista]


def casos():
    sobremesas = filtrar(pratos, categoria="sobremesa")
    yield {"pergunta": "Qual a sobremesa mais barata entre todos os restaurantes?", "tipo": "mais barato",
           "fontes": ids(sobremesas[:1]), "deve_conter": [["pudim"], ["10"]]}

    caro = filtrar(pratos, decrescente=True)[0]
    yield {"pergunta": "Qual o prato mais caro de todos os cardápios?", "tipo": "mais caro",
           "fontes": [caro.id], "deve_conter": [["rodizio"], ["119,90", "119.90"]]}

    baratos = filtrar(pratos, preco_max=14.99)
    yield {"pergunta": "Quais itens custam menos de R$ 15?", "tipo": "lista completa",
           "fontes": ids(baratos), "deve_conter": [["espresso"], ["refrigerante"], ["suco"], ["pudim"],
                                                    ["cappuccino"], ["kombucha"], ["missoshiru"]]}

    veganos = filtrar(pratos, etiquetas=["vegana"])
    yield {"pergunta": "Quantos itens veganos existem somando todos os restaurantes?", "tipo": "contagem",
           "fontes": ids(veganos), "deve_conter": [[str(len(veganos))]]}

    sem_gluten = filtrar(pratos, etiquetas=["sem glúten"], preco_max=30)
    # Só exige os que aparecem em qualquer interpretação de "sem glúten" (etiqueta ou ausência do alergênico)
    yield {"pergunta": "Quais pratos sem glúten custam até R$ 30?", "tipo": "lista completa",
           "fontes": ids(sem_gluten), "deve_conter": [["pudim"], ["salada tropical"], ["mochi"], ["pao de queijo"],
                                                       ["omelete"], ["frango grelhado"]]}

    hamburgueres = filtrar(pratos, restaurante="Brasa", categoria="hambúrguer")
    assert not filtrar(hamburgueres, sem_alergenicos=["lactose"]), "o gabarito supõe que todos têm lactose"
    yield {"pergunta": "Tenho intolerância a lactose: quais hambúrgueres da Brasa & Pão posso pedir?", "tipo": "lista vazia",
           "fontes": ids(hamburgueres), "deve_conter": [["nenhum", "nao ha", "todos", "nao pode"]],
           # Lista vazia é resposta: dizer "não encontrei" e depois "todos têm lactose" é contraditório
           "nao_deve_conter": ["nao encontrei"]}

    vr = [r for r in restaurantes if "vale-refeição" in r.informacoes.get("pagamento", "")
          and "não aceita" not in r.informacoes["pagamento"].lower()]
    yield {"pergunta": "Quais restaurantes aceitam vale-refeição?", "tipo": "comparar restaurantes",
           "fontes": [r.id for r in vr], "deve_conter": [["sakura"], ["raiz verde"], ["lurdes"]],
           "nao_deve_conter": ["forno da vila aceita", "forno da vila, "]}

    picantes = filtrar(pratos, etiquetas=["picante"])
    yield {"pergunta": "Quais são todos os pratos picantes?", "tipo": "lista completa",
           "fontes": ids(picantes), "deve_conter": [["diavola"], ["ceviche"], ["frango crispy"]]}

    pizza = filtrar(pratos, restaurante="Forno", categoria="pizza salgada", etiquetas=["vegetariana"])[0]
    yield {"pergunta": "Qual a pizza salgada vegetariana mais barata do Forno da Vila?", "tipo": "mais barato",
           "fontes": [pizza.id], "deve_conter": [["margherita"], ["49"]]}

    com_entrega = [r for r in restaurantes if not r.informacoes.get("delivery", "").lower().startswith("não")]
    yield {"pergunta": "Quantos restaurantes fazem entrega?", "tipo": "contagem",
           "fontes": [r.id for r in restaurantes], "deve_conter": [[str(len(com_entrega)), "cinco"]]}

    vegano_raiz = filtrar(pratos, restaurante="Raiz Verde", etiquetas=["vegana"])[0]
    yield {"pergunta": "Qual o item vegano mais barato do Raiz Verde?", "tipo": "mais barato",
           "fontes": [vegano_raiz.id], "deve_conter": [["kombucha"], ["14"]]}


if __name__ == "__main__":
    destino = Path(__file__).resolve().parent / "perguntas_agregacao.json"
    lista = list(casos())
    destino.write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(lista)} perguntas em {destino.name}")
