import http.client
import io
import json
import urllib.error

import pytest

from nucleo import kie


def _resposta(dados):
    return io.BytesIO(json.dumps(dados).encode())


def test_validar_mostra_creditos(monkeypatch):
    monkeypatch.setattr(kie.urllib.request, "urlopen",
                        lambda req, timeout: _resposta({"code": 200, "data": 123.5}))
    assert kie.validar("k") == "123.5 créditos"


def test_chave_recusada_vira_erro_amigavel(monkeypatch):
    def recusa(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)
    monkeypatch.setattr(kie.urllib.request, "urlopen", recusa)
    with pytest.raises(kie.KieErro, match="recusou a chave"):
        kie.validar("ruim")


def test_sem_internet_vira_erro_amigavel(monkeypatch):
    def offline(req, timeout):
        raise urllib.error.URLError("sem rede")
    monkeypatch.setattr(kie.urllib.request, "urlopen", offline)
    with pytest.raises(kie.KieErro, match="internet"):
        kie.creditos("k")


def test_code_diferente_de_200_vira_erro(monkeypatch):
    monkeypatch.setattr(kie, "_requisitar", lambda url, chave, dados=None: {"code": 401, "msg": "no"})
    with pytest.raises(kie.KieErro):
        kie.creditos("k")


def test_criar_tarefa_e_aguardar(monkeypatch):
    chamadas = []

    def falso(url, chave, dados=None):
        chamadas.append(url)
        if url.endswith("createTask"):
            assert dados == {"model": "m", "input": {"prompt": "p"}}
            return {"code": 200, "data": {"taskId": "t1"}}
        estado = "waiting" if len(chamadas) < 3 else "success"
        return {"code": 200, "data": {"state": estado, "resultJson": json.dumps({"resultUrls": ["u"]})}}

    monkeypatch.setattr(kie, "_requisitar", falso)
    assert kie.criar_tarefa("k", "m", {"prompt": "p"}) == "t1"
    assert kie.aguardar("k", "t1", intervalo=0, dormir=lambda s: None) == {"resultUrls": ["u"]}


def test_aguardar_falha_da_erro(monkeypatch):
    monkeypatch.setattr(kie, "_requisitar", lambda url, chave, dados=None:
                        {"code": 200, "data": {"state": "fail", "failMsg": "sem crédito"}})
    with pytest.raises(kie.KieErro, match="sem crédito"):
        kie.aguardar("k", "t1", intervalo=0, dormir=lambda s: None)


def _erro_http(codigo):
    return urllib.error.HTTPError("http://x", codigo, "e", {}, None)


def test_baixar_falha_de_rede_vira_erro(monkeypatch, tmp_path):
    def falha(req, timeout):
        raise urllib.error.URLError("caiu")
    monkeypatch.setattr(kie.urllib.request, "urlopen", falha)
    with pytest.raises(kie.KieErro, match="baixar"):
        kie.baixar("http://x/i.png", tmp_path / "a" / "i.png")


def test_baixar_http_e_timeout_viram_erro(monkeypatch, tmp_path):
    for exc in (_erro_http(404), TimeoutError("lento")):
        def falha(req, timeout, exc=exc):
            raise exc
        monkeypatch.setattr(kie.urllib.request, "urlopen", falha)
        with pytest.raises(kie.KieErro, match="Tente de novo"):
            kie.baixar("http://x/i.png", tmp_path / "i.png")


def test_baixar_erro_de_disco_vira_erro(monkeypatch, tmp_path):
    monkeypatch.setattr(kie.urllib.request, "urlopen", lambda req, timeout: io.BytesIO(b"x"))
    (tmp_path / "arquivo").write_text("x")
    with pytest.raises(kie.KieErro, match="baixar"):
        kie.baixar("http://x/i.png", tmp_path / "arquivo" / "i.png")


def test_requisitar_timeout_e_reset_viram_erro(monkeypatch):
    for exc in (TimeoutError(), ConnectionResetError(), http.client.IncompleteRead(b"")):
        def falha(req, timeout, exc=exc):
            raise exc
        monkeypatch.setattr(kie.urllib.request, "urlopen", falha)
        with pytest.raises(kie.KieErro):
            kie.creditos("k")


def test_requisitar_resposta_nao_json_vira_erro(monkeypatch):
    monkeypatch.setattr(kie.urllib.request, "urlopen", lambda req, timeout: io.BytesIO(b"<html>"))
    with pytest.raises(kie.KieErro):
        kie.creditos("k")


def test_429_mensagem_especifica(monkeypatch):
    def falha(req, timeout):
        raise _erro_http(429)
    monkeypatch.setattr(kie.urllib.request, "urlopen", falha)
    with pytest.raises(kie.KieErro, match="muitas requisições"):
        kie.creditos("k")


def test_aguardar_tolera_erros_transitorios(monkeypatch):
    seq = iter([kie.KieErro("x"), kie.KieErro("x"), {"code": 200, "data": {"state": "waiting"}},
                kie.KieErro("x"), kie.KieErro("x"), kie.KieErro("x"),
                {"code": 200, "data": {"state": "success", "resultJson": "{}"}}])

    def falso(url, chave, dados=None):
        r = next(seq)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(kie, "_requisitar", falso)
    assert kie.aguardar("k", "t1", intervalo=0, dormir=lambda s: None) == {}


def test_aguardar_desiste_apos_4_erros_com_task_id(monkeypatch):
    def falso(url, chave, dados=None):
        raise kie.KieErro("rede")
    monkeypatch.setattr(kie, "_requisitar", falso)
    with pytest.raises(kie.KieErro, match="t-123"):
        kie.aguardar("k", "t-123", intervalo=0, dormir=lambda s: None)


def test_aguardar_fail_sem_msg_e_timeout_com_task_id(monkeypatch):
    monkeypatch.setattr(kie, "_requisitar", lambda url, chave, dados=None:
                        {"code": 200, "data": {"state": "fail"}})
    with pytest.raises(kie.KieErro, match="motivo não informado"):
        kie.aguardar("k", "t1", intervalo=0, dormir=lambda s: None)
    monkeypatch.setattr(kie, "_requisitar", lambda url, chave, dados=None:
                        {"code": 200, "data": {"state": "waiting"}})
    with pytest.raises(kie.KieErro, match="t9"):
        kie.aguardar("k", "t9", intervalo=0, limite=0, dormir=lambda s: None)


def test_payload_inesperado_vira_erro(monkeypatch):
    monkeypatch.setattr(kie, "_requisitar", lambda url, chave, dados=None: {"code": 200, "data": {}})
    with pytest.raises(kie.KieErro, match="inesperada"):
        kie.criar_tarefa("k", "m", {})
    monkeypatch.setattr(kie, "_requisitar", lambda url, chave, dados=None:
                        {"code": 200, "data": {"state": "success", "resultJson": "nao-json"}})
    with pytest.raises(kie.KieErro, match="inesperada"):
        kie.aguardar("k", "t1", intervalo=0, dormir=lambda s: None)
    monkeypatch.setattr(kie, "_requisitar", lambda url, chave, dados=None: {"code": 200, "data": "abc"})
    with pytest.raises(kie.KieErro, match="inesperada"):
        kie.creditos("k")


def test_task_id_e_codificado_na_url(monkeypatch):
    vistas = []

    def falso(url, chave, dados=None):
        vistas.append(url)
        return {"code": 200, "data": {"state": "success", "resultJson": "{}"}}
    monkeypatch.setattr(kie, "_requisitar", falso)
    kie.aguardar("k", "a&b=c", intervalo=0, dormir=lambda s: None)
    assert vistas[0].endswith("taskId=a%26b%3Dc")
