import pytest
from fastapi.testclient import TestClient

from app.llm import ErroLLM
from app.main import criar_app
from app.rag import NAO_ENCONTREI
from tests.conftest import LLMFalso


def cliente(indice, llm):
    return TestClient(criar_app(indice=indice, llm=llm))


def test_saude(indice):
    with cliente(indice, LLMFalso("{}")) as c:
        r = c.get("/saude")
    assert r.status_code == 200
    assert r.json()["trechos"] == len(indice.trechos)


def test_lista_os_seis_restaurantes(indice):
    with cliente(indice, LLMFalso("{}")) as c:
        nomes = c.get("/restaurantes").json()["restaurantes"]
    assert len(nomes) == 6
    assert "Sakura Nori" in nomes


def test_perguntar_devolve_resposta_com_fontes(indice):
    llm = LLMFalso({"resposta": "A Margherita custa R$ 49,00.", "fontes": ["forno-da-vila#margherita"]})
    with cliente(indice, llm) as c:
        r = c.post("/perguntar", json={"pergunta": "Quanto custa a Margherita do Forno da Vila?"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["resposta"] == "A Margherita custa R$ 49,00."
    assert corpo["fontes"][0]["id"] == "forno-da-vila#margherita"
    assert corpo["fontes"][0]["restaurante"] == "Forno da Vila"
    assert corpo["modelo"] == "llm-falso"


def test_pergunta_fora_do_escopo(indice):
    with cliente(indice, LLMFalso({"resposta": NAO_ENCONTREI, "fontes": []})) as c:
        corpo = c.post("/perguntar", json={"pergunta": "Qual a previsão do tempo amanhã?"}).json()
    assert corpo == {"resposta": NAO_ENCONTREI, "fontes": [], "modelo": "llm-falso"}


@pytest.mark.parametrize("corpo", [{"pergunta": ""}, {"pergunta": "oi"}, {}, {"pergunta": "pizza?", "k": 0}])
def test_entrada_invalida_da_422(indice, corpo):
    with cliente(indice, LLMFalso("{}")) as c:
        assert c.post("/perguntar", json=corpo).status_code == 422


def test_falha_do_gemini_vira_502(indice):
    class LLMQuebrado(LLMFalso):
        def gerar(self, sistema, prompt):
            raise ErroLLM("Gemini respondeu 429: cota excedida")

    with cliente(indice, LLMQuebrado("{}")) as c:
        r = c.post("/perguntar", json={"pergunta": "Quanto custa a Margherita?"})
    assert r.status_code == 502
    assert "429" in r.json()["detail"]
