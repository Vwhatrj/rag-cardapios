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


def test_timeout_repetido_vira_erro_tratado(monkeypatch):
    import httpx
    import pytest

    from app.llm import ErroLLM, Gemini

    def sempre_timeout(request):
        raise httpx.ReadTimeout("demorou", request=request)

    monkeypatch.setattr("app.llm.time.sleep", lambda _: None)
    g = Gemini(chave="falsa", modelo="gemini-teste")
    g._http = httpx.Client(transport=httpx.MockTransport(sempre_timeout))
    with pytest.raises(ErroLLM, match="Sem resposta"):
        g.gerar("sistema", "pergunta")


def test_cota_diaria_nao_retenta(monkeypatch):
    import httpx
    import pytest

    from app.llm import CotaDiariaEsgotada, Gemini

    chamadas = []

    def cota_esgotada(request):
        chamadas.append(request)
        return httpx.Response(429, json={"error": {"message": "Generate content requests per day limit exceeded"}})

    monkeypatch.setattr("app.llm.time.sleep", lambda _: pytest.fail("não deveria esperar para tentar de novo"))
    g = Gemini(chave="falsa", modelo="gemini-teste")
    g._http = httpx.Client(transport=httpx.MockTransport(cota_esgotada))
    with pytest.raises(CotaDiariaEsgotada):
        g.gerar("sistema", "pergunta")
    assert len(chamadas) == 1


def test_escolhe_flash_lite_estavel_mais_recente():
    ids = ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite-preview",
           "gemini-flash-lite-latest", "gemini-3.8-flash-lite-tts", "gemini-3.1-pro-preview"]
    assert escolher_modelo(ids) == "gemini-3.1-flash-lite"


def _gemini_com_modelos(monkeypatch, ids):
    import httpx

    from app.llm import Gemini

    lista = {"models": [{"name": f"models/{i}", "supportedGenerationMethods": ["generateContent"]} for i in ids]}
    transporte = httpx.MockTransport(lambda request: httpx.Response(200, json=lista))
    original = httpx.Client
    monkeypatch.setattr("app.llm.httpx.Client", lambda **kw: original(transport=transporte, **kw))
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    return Gemini(chave="falsa")


def test_usa_o_modelo_avaliado_quando_disponivel(monkeypatch):
    from app.llm import MODELO_AVALIADO

    g = _gemini_com_modelos(monkeypatch, ["gemini-3.8-flash", "gemini-3.5-flash-lite", MODELO_AVALIADO])
    assert g.nome == MODELO_AVALIADO


def test_modelo_avaliado_aposentado_cai_na_escolha_automatica(monkeypatch):
    g = _gemini_com_modelos(monkeypatch, ["gemini-3.8-flash", "gemini-4.0-flash-lite"])
    assert g.nome == "gemini-4.0-flash-lite"


def test_sem_lite_usa_flash_estavel():
    assert escolher_modelo(["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3-flash-preview"]) == "gemini-3.8-flash"
