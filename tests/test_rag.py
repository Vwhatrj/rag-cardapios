from app.llm import escolher_modelo
from app.rag import NAO_ENCONTREI, SISTEMA, interpretar, responder
from tests.conftest import LLMFalso


def test_prompt_leva_os_trechos_recuperados_e_a_pergunta(indice):
    llm = LLMFalso({"resposta": "ok", "fontes": []})
    responder("Quanto custa a Margherita?", indice, llm, k=3)
    sistema, prompt = llm.chamadas[0]
    assert sistema == SISTEMA
    assert "Pergunta: Quanto custa a Margherita?" in prompt
    assert prompt.count("[") >= 3  # três trechos, cada um com seu [id]


def test_fontes_inventadas_pelo_llm_sao_descartadas(indice):
    recuperados = indice.buscar("Margherita", k=3)
    real = recuperados[0][0].id
    _, fontes = interpretar(f'{{"resposta": "R$ 49", "fontes": ["{real}", "restaurante-fantasma#x"]}}', recuperados)
    assert [t.id for t in fontes] == [real]


def test_json_quebrado_vira_texto_sem_fontes(indice):
    recuperados = indice.buscar("Margherita", k=3)
    resposta, fontes = interpretar("custa 49 reais", recuperados)
    assert resposta == "custa 49 reais"
    assert fontes == []


def test_recusa_nao_cita_fontes(indice):
    llm = LLMFalso({"resposta": NAO_ENCONTREI, "fontes": ["forno-da-vila#info"]})
    r = responder("Qual o telefone do Sakura Nori?", indice, llm)
    assert r.resposta == NAO_ENCONTREI
    assert r.fontes == []


def test_escolhe_flash_estavel_mais_recente():
    ids = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.0-flash-preview", "gemini-2.5-flash-lite"]
    assert escolher_modelo(ids) == "gemini-2.5-flash"
