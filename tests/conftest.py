import json

import pytest

from app.busca import Indice, embedder_e5
from app.cardapios import carregar_trechos
from app.catalogo import carregar_catalogo
from app.ferramentas import Ferramentas


class LLMFalso:
    """Substitui o Gemini nos testes: devolve uma resposta fixa e guarda o que recebeu."""

    nome = "llm-falso"

    def __init__(self, resposta: str | dict):
        self.resposta = resposta if isinstance(resposta, str) else json.dumps(resposta, ensure_ascii=False)
        self.chamadas: list[tuple[str, str]] = []

    def gerar(self, sistema: str, prompt: str) -> str:
        self.chamadas.append((sistema, prompt))
        return self.resposta


class AgenteFalso(LLMFalso):
    """Simula o Gemini com ferramentas: cada item do roteiro é a resposta de um turno.

    Um turno é uma lista de chamadas {"nome": ..., "args": ...} ou um texto final.
    """

    def __init__(self, roteiro: list[list[dict] | str]):
        super().__init__("{}")
        self.roteiro = list(roteiro)
        self.historicos: list[list[dict]] = []

    def conversar(self, sistema: str, conteudos: list[dict], ferramentas: list[dict]) -> list[dict]:
        self.historicos.append([dict(c) for c in conteudos])
        turno = self.roteiro.pop(0)
        if isinstance(turno, str):
            return [{"text": turno}]
        return [{"functionCall": {"name": c["nome"], "args": c.get("args", {})}} for c in turno]


@pytest.fixture(scope="session")
def ferramentas(indice):
    return Ferramentas(*carregar_catalogo(), indice)


@pytest.fixture(scope="session")
def trechos():
    return carregar_trechos()


@pytest.fixture(scope="session")
def indice(trechos):
    # Usa o modelo de embeddings de verdade: a qualidade da busca é justamente o que queremos testar
    return Indice(trechos, *embedder_e5())
