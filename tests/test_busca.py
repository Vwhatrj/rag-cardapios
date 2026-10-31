import pytest


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("Tem pizza vegana?", "forno-da-vila#vegana-de-abobrinha"),
        ("Que horas a Cantina Dona Lurdes abre?", "cantina-dona-lurdes#info"),
        ("Quanto custa o temaki de salmão?", "sakura-nori#temaki-de-salmao"),
        ("Tem algum doce sem açúcar para diabético?", "doce-atelie#brownie-sem-acucar"),
        ("Qual hambúrguer é apimentado?", "brasa-e-pao#frango-crispy"),
    ],
)
def test_trecho_certo_aparece_entre_os_primeiros(indice, pergunta, esperado):
    ids = [t.id for t, _ in indice.buscar(pergunta, k=5)]
    assert esperado in ids, f"{esperado} não está no top 5: {ids}"


def test_resultados_vem_ordenados_por_similaridade(indice):
    notas = [nota for _, nota in indice.buscar("sobremesa de chocolate", k=8)]
    assert notas == sorted(notas, reverse=True)


def test_k_limita_a_quantidade(indice):
    assert len(indice.buscar("pizza", k=3)) == 3
