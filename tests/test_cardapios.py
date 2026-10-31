from app.cardapios import carregar_trechos, slug


def test_slug_remove_acentos_e_simbolos():
    assert slug("Pão de Queijo (porção com 6)") == "pao-de-queijo-porcao-com-6"


def test_cada_restaurante_tem_trecho_de_informacoes(trechos):
    restaurantes = {t.restaurante for t in trechos}
    infos = {t.restaurante for t in trechos if t.id.endswith("#info")}
    assert len(restaurantes) == 6
    assert infos == restaurantes


def test_ids_sao_unicos(trechos):
    assert len({t.id for t in trechos}) == len(trechos)


def test_trecho_de_prato_carrega_restaurante_e_preco(trechos):
    margherita = next(t for t in trechos if t.id == "forno-da-vila#margherita")
    assert margherita.restaurante == "Forno da Vila"
    assert "Forno da Vila" in margherita.texto  # sem isso o prato perde o contexto na busca
    assert "R$ 49,00" in margherita.texto


def test_carregar_e_deterministico():
    assert [t.id for t in carregar_trechos()] == [t.id for t in carregar_trechos()]
