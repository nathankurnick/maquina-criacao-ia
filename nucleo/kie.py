"""Cliente KIE (Nano Banana pra imagem; Kling no modo avançado)."""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from nucleo.erros import MaquinaErro

BASE = "https://api.kie.ai/api/v1"


class KieErro(MaquinaErro):
    pass


def _requisitar(url: str, chave: str, dados: "dict | None" = None) -> dict:
    headers = {"Authorization": f"Bearer {chave}"}
    corpo = None
    if dados is not None:
        corpo = json.dumps(dados).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=corpo, headers=headers,
                                 method="POST" if corpo else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise KieErro("A KIE recusou a chave. Confira em https://kie.ai/api-key e rode: maquina chaves") from e
        raise KieErro(f"A KIE respondeu com erro {e.code}. Tente de novo em alguns minutos.") from e
    except urllib.error.URLError as e:
        raise KieErro("Não consegui falar com a KIE. Confira sua internet e tente de novo.") from e


def _checar(d: dict) -> dict:
    if d.get("code") != 200:
        raise KieErro(f"A KIE recusou o pedido: {d.get('msg') or d}. Confira a chave e os créditos.")
    return d


def creditos(chave: str) -> float:
    return float(_checar(_requisitar(f"{BASE}/chat/credit", chave)).get("data") or 0)


def validar(chave: str) -> str:
    return f"{creditos(chave):g} créditos"


def criar_tarefa(chave: str, modelo: str, entrada: dict) -> str:
    d = _checar(_requisitar(f"{BASE}/jobs/createTask", chave, {"model": modelo, "input": entrada}))
    return d["data"]["taskId"]


def aguardar(chave: str, task_id: str, intervalo: float = 15, limite: float = 1800,
             dormir=time.sleep) -> dict:
    inicio = time.monotonic()
    while time.monotonic() - inicio < limite:
        d = _checar(_requisitar(f"{BASE}/jobs/recordInfo?taskId={task_id}", chave))["data"]
        if d.get("state") == "success":
            return json.loads(d["resultJson"])
        if d.get("state") == "fail":
            raise KieErro(f"A KIE não conseguiu gerar: {d.get('failMsg')}")
        dormir(intervalo)
    raise KieErro("A KIE demorou demais pra responder. Tente de novo mais tarde.")


def baixar(url: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        destino.write_bytes(r.read())
    return destino
