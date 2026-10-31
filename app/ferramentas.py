"""Ferramentas que o agente pode chamar. Cada uma tem uma declaração (o que o modelo lê) e uma implementação."""
from app.busca import Indice
from app.catalogo import Prato, Restaurante, filtrar, normalizar

# Formato de "functionDeclarations" da API do Gemini (subconjunto do OpenAPI)
DECLARACOES = [
    {
        "name": "filtrar_pratos",
        "description": (
            "Filtra a lista COMPLETA de pratos de todos os restaurantes por preço, etiqueta, alergênico, categoria "
            "ou restaurante, e ordena. Use para perguntas com 'mais barato', 'mais caro', 'até R$ X', 'todos os', "
            "'quais', 'quantos' ou que comparam restaurantes. Todos os filtros são opcionais e se combinam (E)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "preco_max": {"type": "NUMBER", "description": "Preço máximo em reais, inclusive."},
                "preco_min": {"type": "NUMBER", "description": "Preço mínimo em reais, inclusive."},
                "etiquetas": {"type": "ARRAY", "items": {"type": "STRING"},
                              "description": "O prato precisa ter TODAS. Valores existentes: vegana, vegetariana, "
                                             "sem glúten, sem lactose, sem açúcar, picante."},
                "sem_alergenicos": {"type": "ARRAY", "items": {"type": "STRING"},
                                    "description": "Exclui pratos com qualquer um destes alergênicos. Ex.: glúten, "
                                                   "lactose, castanhas, amêndoa, nozes, ovo, peixe, crustáceos, soja, gergelim."},
                "categoria": {"type": "STRING", "description": "Trecho do nome da categoria. Ex.: pizza, sobremesa, "
                                                               "bebida, hambúrguer, prato feito, entrada, café."},
                "restaurante": {"type": "STRING", "description": "Trecho do nome do restaurante."},
                "ordenar_por": {"type": "STRING", "enum": ["preco", "nome"]},
                "decrescente": {"type": "BOOLEAN", "description": "true para do mais caro ao mais barato."},
                "limite": {"type": "INTEGER", "description": "Máximo de pratos devolvidos (padrão 15)."},
            },
        },
    },
    {
        "name": "buscar_cardapio",
        "description": (
            "Busca semântica nos cardápios: devolve os trechos mais parecidos com a consulta. Use para perguntas "
            "sobre um prato ou assunto específico (ingredientes, descrição, tamanho, adicionais) que não se resolvem "
            "com filtros."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "consulta": {"type": "STRING", "description": "O que procurar, em linguagem natural."},
                "k": {"type": "INTEGER", "description": "Quantos trechos devolver (padrão 5)."},
            },
            "required": ["consulta"],
        },
    },
    {
        "name": "info_restaurantes",
        "description": (
            "Informações gerais dos restaurantes: tipo, endereço, horário e dias de funcionamento, entrega e taxa, "
            "formas de pagamento e observações. Sem argumento, devolve todos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {"restaurante": {"type": "STRING", "description": "Trecho do nome do restaurante (opcional)."}},
        },
    },
]


class Ferramentas:
    def __init__(self, pratos: list[Prato], restaurantes: list[Restaurante], indice: Indice):
        self.pratos = pratos
        self.restaurantes = restaurantes
        self.indice = indice

    def executar(self, nome: str, args: dict) -> tuple[dict, list[str]]:
        """Devolve (resultado para o modelo, ids das fontes que apareceram no resultado).

        Erros viram um resultado com 'erro', para o modelo poder corrigir a chamada em vez de a API cair.
        """
        try:
            if nome == "filtrar_pratos":
                return self._filtrar(**args)
            if nome == "buscar_cardapio":
                return self._buscar(**args)
            if nome == "info_restaurantes":
                return self._info(**args)
            return {"erro": f"Ferramenta desconhecida: {nome}"}, []
        except TypeError as erro:
            return {"erro": f"Argumentos inválidos para {nome}: {erro}"}, []

    def _filtrar(self, limite: int = 15, **filtros) -> tuple[dict, list[str]]:
        achados = filtrar(self.pratos, **filtros)
        mostrados = achados[: max(1, int(limite))]
        return {"total_encontrado": len(achados), "pratos": [p.resumo() for p in mostrados]}, [p.id for p in mostrados]

    def _buscar(self, consulta: str, k: int = 5) -> tuple[dict, list[str]]:
        trechos = [t for t, _ in self.indice.buscar(consulta, k=max(1, min(int(k), 10)))]
        return {"trechos": [{"id": t.id, "texto": t.texto} for t in trechos]}, [t.id for t in trechos]

    def _info(self, restaurante: str | None = None) -> tuple[dict, list[str]]:
        escolhidos = [r for r in self.restaurantes if not restaurante or normalizar(restaurante) in normalizar(r.nome)]
        return ({"restaurantes": [{"id": r.id, "restaurante": r.nome, **r.informacoes} for r in escolhidos]},
                [r.id for r in escolhidos])
