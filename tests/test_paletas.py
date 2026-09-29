import pagina_conteudo
from nucleo import paletas


def test_paletas_do_nucleo_iguais_as_do_02():
    assert paletas.PALETAS == pagina_conteudo.PALETAS
    assert paletas.PALETAS_ROTULO == pagina_conteudo.PALETAS_ROTULO
    assert paletas.PALETA_PADRAO == pagina_conteudo.PALETA_PADRAO


def test_paleta_desconhecida_cai_na_padrao():
    assert paletas.paleta("rosa") == paletas.PALETAS["azul-laranja"]
    assert paletas.paleta("preto-dourado")["destaque"] == "#d4af37"
