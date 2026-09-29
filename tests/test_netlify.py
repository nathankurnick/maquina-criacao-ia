import http.client
import io
import urllib.error
import zipfile

import pytest

from nucleo import netlify


def test_validar_devolve_email(monkeypatch):
    monkeypatch.setattr(netlify, "_requisitar", lambda m, c, t, corpo=None, tipo="": {"email": "a@b.com"})
    assert netlify.validar("t") == "a@b.com"


def test_publicar_cria_site_e_sobe_zip(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<h1>oi</h1>")
    (tmp_path / "img").mkdir()
    (tmp_path / "img" / "a.png").write_bytes(b"png")
    chamadas = []

    def falso(metodo, caminho, token, corpo=None, tipo="application/json"):
        chamadas.append((metodo, caminho, tipo))
        if caminho == "/sites":
            return {"id": "s1"}
        nomes = zipfile.ZipFile(io.BytesIO(corpo)).namelist()
        assert sorted(nomes) == ["img/a.png", "index.html"]
        return {"ssl_url": "https://x.netlify.app"}

    monkeypatch.setattr(netlify, "_requisitar", falso)
    r = netlify.publicar_pasta("t", tmp_path)
    assert r == {"site_id": "s1", "url": "https://x.netlify.app"}
    assert chamadas == [("POST", "/sites", "application/json"),
                        ("POST", "/sites/s1/deploys", "application/zip")]


def test_republicar_nao_cria_site_novo(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("x")
    caminhos = []
    monkeypatch.setattr(netlify, "_requisitar",
                        lambda m, c, t, corpo=None, tipo="": caminhos.append(c) or {"ssl_url": "u"})
    netlify.publicar_pasta("t", tmp_path, site_id="s9")
    assert caminhos == ["/sites/s9/deploys"]


def test_pasta_sem_index_da_erro(tmp_path):
    with pytest.raises(netlify.NetlifyErro, match="index.html"):
        netlify.publicar_pasta("t", tmp_path)


def _http_erro(codigo):
    return urllib.error.HTTPError("u", codigo, "x", {}, io.BytesIO(b""))


def _urlopen_que_levanta(monkeypatch, exc):
    def falso(req, timeout=None):
        raise exc
    monkeypatch.setattr(netlify.urllib.request, "urlopen", falso)


@pytest.mark.parametrize("codigo,trecho", [(401, "recusou o token"), (403, "recusou o token"),
                                           (429, "muitas requisições"), (500, "erro 500")])
def test_erros_http_viram_mensagem_amigavel(monkeypatch, codigo, trecho):
    _urlopen_que_levanta(monkeypatch, _http_erro(codigo))
    with pytest.raises(netlify.NetlifyErro, match=trecho):
        netlify._requisitar("GET", "/user", "t")


@pytest.mark.parametrize("exc", [urllib.error.URLError("sem rede"), TimeoutError("lento"),
                                 ConnectionResetError("reset"), http.client.IncompleteRead(b"x")])
def test_falha_de_rede_vira_netlify_erro(monkeypatch, exc):
    _urlopen_que_levanta(monkeypatch, exc)
    with pytest.raises(netlify.NetlifyErro, match="Não consegui falar com a Netlify"):
        netlify._requisitar("GET", "/user", "t")


def test_corpo_nao_json_vira_netlify_erro(monkeypatch):
    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(netlify.urllib.request, "urlopen", lambda req, timeout=None: Resp(b"<html>oops"))
    with pytest.raises(netlify.NetlifyErro, match="resposta inesperada"):
        netlify._requisitar("GET", "/user", "t")


def test_criar_site_sem_id_vira_netlify_erro(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("x")
    monkeypatch.setattr(netlify, "_requisitar", lambda m, c, t, corpo=None, tipo="": {})
    with pytest.raises(netlify.NetlifyErro, match="resposta inesperada"):
        netlify.publicar_pasta("t", tmp_path)


def test_json_que_nao_e_objeto_vira_netlify_erro(monkeypatch):
    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(netlify.urllib.request, "urlopen", lambda req, timeout=None: Resp(b"[1]"))
    with pytest.raises(netlify.NetlifyErro, match="resposta inesperada"):
        netlify._requisitar("GET", "/user", "t")
