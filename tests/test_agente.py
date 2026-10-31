from fastapi.testclient import TestClient

from app import agente
from app.main import criar_app
from app.rag import NAO_ENCONTREI
from tests.conftest import AgenteFalso


def test_chama_ferramenta_e_responde_com_fontes(ferramentas):
    llm = AgenteFalso([
        [{"nome": "filtrar_pratos", "args": {"categoria": "sobremesa", "limite": 1}}],
        "A sobremesa mais barata é o Pudim de Leite, R$ 10,00, da Cantina Dona Lurdes.\nFONTES: cantina-dona-lurdes#pudim-de-leite",
    ])
    r = agente.responder("Qual a sobremesa mais barata?", ferramentas, llm)
    assert r.resposta.startswith("A sobremesa mais barata é o Pudim")
    assert "FONTES" not in r.resposta
    assert r.fontes == ["cantina-dona-lurdes#pudim-de-leite"]
    assert [(p.ferramenta, p.resultados) for p in r.passos] == [("filtrar_pratos", 1)]


def test_resultado_da_ferramenta_volta_para_o_modelo(ferramentas):
    llm = AgenteFalso([[{"nome": "filtrar_pratos", "args": {"etiquetas": ["picante"]}}], "ok\nFONTES: nenhuma"])
    agente.responder("Quais pratos são picantes?", ferramentas, llm)
    ultimo = llm.historicos[-1][-1]
    resposta = ultimo["parts"][0]["functionResponse"]
    assert ultimo["role"] == "user"
    assert resposta["response"]["total_encontrado"] == 3


def test_fonte_que_nenhuma_ferramenta_devolveu_e_descartada(ferramentas):
    llm = AgenteFalso([
        [{"nome": "info_restaurantes", "args": {"restaurante": "Sakura"}}],
        "Fecha domingo à noite.\nFONTES: sakura-nori#info, forno-da-vila#margherita",
    ])
    assert agente.responder("Sakura abre domingo à noite?", ferramentas, llm).fontes == ["sakura-nori#info"]


def test_chamadas_em_paralelo_e_varios_turnos(ferramentas):
    llm = AgenteFalso([
        [{"nome": "info_restaurantes"}, {"nome": "filtrar_pratos", "args": {"etiquetas": ["vegana"], "limite": 3}}],
        [{"nome": "buscar_cardapio", "args": {"consulta": "kombucha"}}],
        "Resposta.\nFONTES: raiz-verde#kombucha-da-casa",
    ])
    r = agente.responder("pergunta composta", ferramentas, llm)
    assert [p.ferramenta for p in r.passos] == ["info_restaurantes", "filtrar_pratos", "buscar_cardapio"]
    assert r.fontes == ["raiz-verde#kombucha-da-casa"]


def test_argumento_invalido_vira_erro_para_o_modelo_corrigir(ferramentas):
    llm = AgenteFalso([[{"nome": "filtrar_pratos", "args": {"cor": "azul"}}], f"{NAO_ENCONTREI}\nFONTES: nenhuma"])
    r = agente.responder("pratos azuis?", ferramentas, llm)
    devolvido = llm.historicos[-1][-1]["parts"][0]["functionResponse"]["response"]
    assert "erro" in devolvido
    assert r.resposta == NAO_ENCONTREI
    assert r.fontes == []


def test_para_depois_do_limite_de_passos(ferramentas):
    llm = AgenteFalso([[{"nome": "info_restaurantes"}]] * 10)
    r = agente.responder("loop", ferramentas, llm, max_passos=3)
    assert r.resposta == agente.NAO_CONCLUIU
    assert len(r.passos) == 3


def test_rota_agente(indice):
    llm = AgenteFalso([
        [{"nome": "filtrar_pratos", "args": {"decrescente": True, "limite": 1}}],
        "O mais caro é o Rodízio Completo.\nFONTES: sakura-nori#rodizio-completo",
    ])
    with TestClient(criar_app(indice=indice, llm=llm)) as c:
        corpo = c.post("/agente", json={"pergunta": "Qual o prato mais caro?"}).json()
    assert corpo["resposta"] == "O mais caro é o Rodízio Completo."
    assert corpo["fontes"][0]["restaurante"] == "Sakura Nori"
    assert corpo["passos"] == [{"ferramenta": "filtrar_pratos", "argumentos": {"decrescente": True, "limite": 1}, "resultados": 1}]
