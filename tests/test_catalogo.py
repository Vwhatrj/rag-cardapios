import pytest

from app.catalogo import carregar_catalogo, filtrar


@pytest.fixture(scope="module")
def pratos():
    return carregar_catalogo()[0]


def nomes(lista):
    return [p.nome for p in lista]


def test_todo_prato_tem_preco_numerico(pratos):
    assert len(pratos) == 50
    assert all(p.preco is not None for p in pratos)


def test_ids_batem_com_os_trechos_da_busca(pratos, trechos):
    # O agente cita ids de pratos; a API transforma em trechos. Os dois lados precisam usar o mesmo id.
    assert {p.id for p in pratos} <= {t.id for t in trechos}


def test_preco_usa_o_primeiro_valor_do_texto(pratos):
    feijoada = next(p for p in pratos if p.nome == "Feijoada Completa")
    assert feijoada.preco == 45.0
    assert "82,00" in feijoada.preco_texto


def test_etiqueta_ignora_genero_e_acento(pratos):
    assert nomes(filtrar(pratos, etiquetas=["vegano"])) == nomes(filtrar(pratos, etiquetas=["VEGANA"]))
    assert "Salada Tropical" in nomes(filtrar(pratos, etiquetas=["sem gluten"]))


def test_filtros_se_combinam(pratos):
    assert nomes(filtrar(pratos, etiquetas=["picante"])) == ["Frango Crispy", "Ceviche de Peixe Branco", "Diavola"]
    assert nomes(filtrar(pratos, categoria="sobremesa", preco_max=16)) == ["Pudim de Leite", "Brownie de Cacau"]


def test_sem_alergenico_e_conservador(pratos):
    # "pode conter glúten na farofa" também exclui a feijoada de quem pediu sem glúten
    assert "Feijoada Completa" not in nomes(filtrar(pratos, sem_alergenicos=["glúten"]))
    assert filtrar(pratos, restaurante="brasa", categoria="hamburguer", sem_alergenicos=["lactose"]) == []


def test_ordena_do_mais_caro(pratos):
    assert filtrar(pratos, decrescente=True)[0].nome == "Rodízio Completo"
