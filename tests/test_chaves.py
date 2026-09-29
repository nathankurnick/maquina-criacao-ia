import stat

import pytest

from nucleo import chaves
from nucleo.erros import MaquinaErro


def test_sem_arquivo_nao_ha_chaves(ambiente):
    assert chaves.ler_chaves() == {}
    assert chaves.obter_chave("KIE_API_KEY") is None


def test_salvar_cria_arquivo_600_e_preserva_outras(ambiente):
    chaves.salvar_chave("KIE_API_KEY", "kie123")
    chaves.salvar_chave("NETLIFY_TOKEN", "net456")
    chaves.salvar_chave("KIE_API_KEY", "kie789")
    arq = chaves.arquivo_chaves()
    assert stat.S_IMODE(arq.stat().st_mode) == 0o600
    assert stat.S_IMODE(arq.parent.stat().st_mode) == 0o700
    assert chaves.ler_chaves() == {"KIE_API_KEY": "kie789", "NETLIFY_TOKEN": "net456"}


def test_nome_desconhecido_da_erro(ambiente):
    with pytest.raises(MaquinaErro):
        chaves.salvar_chave("OUTRA", "x")


def test_env_tem_prioridade(ambiente, monkeypatch):
    chaves.salvar_chave("KIE_API_KEY", "arquivo")
    monkeypatch.setenv("KIE_API_KEY", "env")
    assert chaves.obter_chave("KIE_API_KEY") == "env"


def test_testar_chave_despacha_pro_servico(monkeypatch):
    monkeypatch.setattr(chaves.kie, "validar", lambda v: f"kie:{v}")
    monkeypatch.setattr(chaves.netlify, "validar", lambda v: f"net:{v}")
    assert chaves.testar_chave("KIE_API_KEY", "a") == "kie:a"
    assert chaves.testar_chave("NETLIFY_TOKEN", "b") == "net:b"


@pytest.mark.parametrize("valor", ["", "   ", "abc def", "abc\ndef", "abc​def", "chávé", "a\tb"])
def test_salvar_rejeita_valor_estranho(ambiente, valor):
    with pytest.raises(MaquinaErro, match="caracteres estranhos"):
        chaves.salvar_chave("KIE_API_KEY", valor)
    assert not chaves.arquivo_chaves().exists()


def test_salvar_arquivo_preexistente_0644_termina_0600(ambiente):
    arq = chaves.arquivo_chaves()
    arq.parent.mkdir(parents=True)
    arq.write_text("NETLIFY_TOKEN=n\n")
    arq.chmod(0o644)
    chaves.salvar_chave("KIE_API_KEY", "k")
    assert stat.S_IMODE(arq.stat().st_mode) == 0o600
    assert chaves.ler_chaves() == {"NETLIFY_TOKEN": "n", "KIE_API_KEY": "k"}
    assert [p.name for p in arq.parent.iterdir()] == ["chaves.env"]


def test_valor_com_igual_faz_ida_e_volta(ambiente):
    chaves.salvar_chave("KIE_API_KEY", "abc==def=")
    assert chaves.ler_chaves()["KIE_API_KEY"] == "abc==def="


def test_salvar_remove_tmp_orfaos(ambiente):
    chaves.salvar_chave("KIE_API_KEY", "a")
    velho = chaves.arquivo_chaves().parent / ".chaves.env.deadbeef.tmp"
    velho.write_text("lixo")
    chaves.salvar_chave("KIE_API_KEY", "b")
    assert not velho.exists()
    assert chaves.ler_chaves() == {"KIE_API_KEY": "b"}
