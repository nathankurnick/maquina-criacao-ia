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
