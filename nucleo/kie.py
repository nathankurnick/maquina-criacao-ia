"""Cliente KIE (Nano Banana pra imagem; Kling no modo avançado)."""
import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from nucleo.erros import MaquinaErro

BASE = "https://api.kie.ai/api/v1"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


class KieErro(MaquinaErro):
    pass


class KieErroPermanente(KieErro):
    """Repetir não adianta (chave/pedido inválido, tarefa falhou)."""


def _requisitar(url: str, chave: str, dados: "dict | None" = None) -> dict:
    headers = {"Authorization": f"Bearer {chave}", "User-Agent": USER_AGENT}
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
            raise KieErroPermanente("A KIE recusou a chave. Confira em https://kie.ai/api-key e rode: maquina chaves") from e
        if e.code == 429:
            raise KieErro("A KIE recebeu muitas requisições. Espere um minuto e tente de novo.") from e
        if e.code in (400, 404, 422):
            raise KieErroPermanente(f"A KIE recusou o pedido (erro {e.code}). Confira os dados e tente de novo.") from e
        raise KieErro(f"A KIE respondeu com erro {e.code}. Tente de novo em alguns minutos.") from e
    except (OSError, http.client.HTTPException) as e:  # URLError e TimeoutError são OSError
        raise KieErro("Não consegui falar com a KIE. Confira sua internet e tente de novo.") from e
    except ValueError as e:
        raise KieErro("A KIE devolveu uma resposta inesperada. Tente de novo em alguns minutos.") from e


def _checar(d: dict) -> dict:
    codigo = d.get("code")
    if codigo == 200:
        return d
    if isinstance(codigo, int) and (codigo in (429, 455) or (codigo >= 500 and codigo != 501)):
        raise KieErro("A KIE está instável ou ocupada agora. Tente de novo em alguns minutos.")
    if codigo == 402:
        raise KieErroPermanente("Seus créditos da KIE acabaram. Recarregue em https://kie.ai e tente de novo.")
    raise KieErroPermanente(f"A KIE recusou o pedido: {d.get('msg') or d}. Confira a chave e os créditos.")


INESPERADA = "A KIE devolveu uma resposta inesperada. Tente de novo em alguns minutos."


def creditos(chave: str) -> float:
    try:
        return float(_checar(_requisitar(f"{BASE}/chat/credit", chave)).get("data") or 0)
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise KieErro(INESPERADA) from e


def validar(chave: str) -> str:
    return f"{creditos(chave):g} créditos"


def criar_tarefa(chave: str, modelo: str, entrada: dict) -> str:
    try:
        d = _checar(_requisitar(f"{BASE}/jobs/createTask", chave, {"model": modelo, "input": entrada}))
        return d["data"]["taskId"]
    except (KeyError, TypeError, AttributeError) as e:
        raise KieErro(INESPERADA) from e


def aguardar(chave: str, task_id: str, intervalo: float = 15, limite: float = 1800,
             dormir=time.sleep) -> dict:
    url = f"{BASE}/jobs/recordInfo?taskId={urllib.parse.quote(task_id, safe='')}"
    inicio = time.monotonic()
    falhas = 0
    while time.monotonic() - inicio < limite:
        try:
            d = _checar(_requisitar(url, chave))["data"]
            estado = d.get("state")
            if estado == "success":
                return json.loads(d["resultJson"])
            if estado == "fail":
                raise KieErroPermanente(f"A KIE não conseguiu gerar: {d.get('failMsg') or 'motivo não informado'}")
            falhas = 0
        except KieErroPermanente:
            raise
        except KieErro as e:
            falhas += 1
            if falhas > 3:
                raise KieErro(f"Perdi a conexão com a KIE ({e}). Sua tarefa continua lá: "
                              f"guarde o código {task_id} e tente de novo.") from e
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            raise KieErro(INESPERADA) from e
        dormir(intervalo)
    raise KieErro(f"A KIE demorou demais pra responder (tarefa {task_id}). Tente de novo mais tarde.")


def baixar(url: str, destino: Path) -> Path:
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as r:
            destino.write_bytes(r.read())
    except (OSError, http.client.HTTPException) as e:  # inclui HTTPError, URLError, timeout, disco
        raise KieErro("O arquivo foi gerado, mas não consegui baixar. Tente de novo.") from e
    return destino
