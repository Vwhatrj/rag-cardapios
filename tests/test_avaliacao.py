import json
from pathlib import Path

from avaliacao.avaliar import avaliar_resposta

CASOS = json.loads((Path(__file__).resolve().parent.parent / "avaliacao" / "perguntas.json").read_text(encoding="utf-8"))


def test_fontes_esperadas_existem_nos_cardapios(trechos):
    # Se alguém renomear um prato, a avaliação tem que quebrar aqui, e não medir errado em silêncio
    ids = {t.id for t in trechos}
    for caso in CASOS:
        assert set(caso.get("fontes", [])) <= ids, caso["pergunta"]


def test_checagem_ignora_acentos_e_maiusculas():
    caso = {"fontes": ["x#info"], "deve_conter": [["sabado"]]}
    assert avaliar_resposta(caso, "Só aos SÁBADOS.", ["x#info"])["resposta_ok"]


def test_resposta_com_trecho_proibido_reprova():
    caso = {"fontes": ["x#a"], "deve_conter": [["gluten"]], "nao_deve_conter": ["nao tem gluten"]}
    assert not avaliar_resposta(caso, "Não tem glúten.", ["x#a"])["resposta_ok"]


def test_fora_do_escopo_exige_recusa_sem_fontes():
    caso = {"fora_do_escopo": True}
    assert avaliar_resposta(caso, "Não encontrei essa informação nos cardápios.", [])["resposta_ok"]
    assert not avaliar_resposta(caso, "O telefone é 1234-5678.", [])["resposta_ok"]
