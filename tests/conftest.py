import json

import pytest

from app.busca import Indice, embedder_e5
from app.cardapios import carregar_trechos


class LLMFalso:
    """Substitui o Gemini nos testes: devolve uma resposta fixa e guarda o que recebeu."""

    nome = "llm-falso"

    def __init__(self, resposta: str | dict):
        self.resposta = resposta if isinstance(resposta, str) else json.dumps(resposta, ensure_ascii=False)
        self.chamadas: list[tuple[str, str]] = []

    def gerar(self, sistema: str, prompt: str) -> str:
        self.chamadas.append((sistema, prompt))
        return self.resposta


@pytest.fixture(scope="session")
def trechos():
    return carregar_trechos()


@pytest.fixture(scope="session")
def indice(trechos):
    # Usa o modelo de embeddings de verdade: a qualidade da busca é justamente o que queremos testar
    return Indice(trechos, *embedder_e5())
