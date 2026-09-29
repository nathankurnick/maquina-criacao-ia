import pytest

from nucleo.erros import MaquinaErro
from nucleo.projeto import (
    Oferta, SUBPASTAS, abrir_projeto, campos_faltando, criar_projeto,
    ler_oferta, listar_projetos, salvar_oferta, slugify,
)


def test_slugify_tira_acento_e_espaco():
    assert slugify("  Protocolo Barriga Léve 2.0! ") == "protocolo-barriga-leve-2-0"


def test_slugify_vazio_da_erro():
    with pytest.raises(MaquinaErro):
        slugify("!!!")


def test_criar_projeto_cria_subpastas_e_e_idempotente(ambiente):
    p = criar_projeto("Método Costela")
    assert p == ambiente / "projetos" / "metodo-costela"
    for s in SUBPASTAS:
        assert (p / s).is_dir()
    assert criar_projeto("Método Costela") == p


def test_listar_e_abrir(ambiente):
    assert listar_projetos() == []
    criar_projeto("B produto")
    criar_projeto("A produto")
    assert listar_projetos() == ["a-produto", "b-produto"]
    assert abrir_projeto("a-produto").is_dir()
    with pytest.raises(MaquinaErro, match="não existe"):
        abrir_projeto("nao-tem")


def test_salvar_e_ler_oferta_ida_e_volta(ambiente):
    p = criar_projeto("Teste")
    o = Oferta(nome="Teste", nicho="culinária", preco="R$ 47",
               entregaveis=["Ebook", "Checklist"], bonus=["Planner"],
               corpo="Notas livres aqui.")
    salvar_oferta(p, o)
    lida = ler_oferta(p)
    assert lida == o
    assert (p / "oferta.md").read_text().startswith("---\n")


def test_ler_oferta_inexistente_devolve_none(ambiente):
    assert ler_oferta(criar_projeto("Vazio")) is None


def test_ler_oferta_ignora_chave_desconhecida_e_normaliza_tipos(ambiente):
    p = criar_projeto("Manual")
    (p / "oferta.md").write_text(
        "---\nnome: Manual\npreco: 47\nentregaveis: Ebook\nextra: x\n---\nCorpo\n",
        encoding="utf-8",
    )
    o = ler_oferta(p)
    assert o.preco == "47"
    assert o.entregaveis == ["Ebook"]
    assert o.corpo == "Corpo"


def test_ler_oferta_com_yaml_quebrado_da_erro_amigavel(ambiente):
    p = criar_projeto("Quebrado")
    (p / "oferta.md").write_text("---\nnome: [sem fechar\n---\n", encoding="utf-8")
    with pytest.raises(MaquinaErro, match="oferta.md"):
        ler_oferta(p)


def test_campos_faltando():
    assert campos_faltando(Oferta(nome="X", preco="R$ 10")) == [
        "nicho", "avatar", "promessa", "mecanismo",
    ]
