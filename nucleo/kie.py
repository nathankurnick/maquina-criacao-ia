"""Cliente KIE (Nano Banana pra imagem; Kling no modo avançado)."""
import base64
import http.client
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from nucleo import png
from nucleo.erros import MaquinaErro

BASE = "https://api.kie.ai/api/v1"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
UPLOAD = "https://kieai.redpandaai.co/api/file-base64-upload"
LIMITE_UPLOAD = 8 * 1024 * 1024
MODELO_SEM_FUNDO = "recraft/remove-background"


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


_ASSINATURAS = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")


def _e_imagem(arq: Path) -> bool:
    try:
        with open(arq, "rb") as f:
            cab = f.read(12)
    except OSError:
        return False
    return cab.startswith(_ASSINATURAS) or (cab[:4] == b"RIFF" and cab[8:12] == b"WEBP")


def enviar_arquivo(chave: str, arquivo: Path) -> str:
    """Sobe uma imagem local pra KIE e devolve a URL pública (vale por ~1 dia)."""
    arquivo = Path(arquivo)
    try:
        dados = arquivo.read_bytes()
    except OSError as e:
        raise KieErroPermanente(f"Não consegui ler {arquivo.name} pra enviar à KIE.") from e
    if len(dados) > LIMITE_UPLOAD:
        raise KieErroPermanente(f"A imagem {arquivo.name} é grande demais pra enviar à KIE (máx. 8 MB).")
    if dados.startswith(b"\x89PNG"):
        mime, ext = "image/png", ".png"
    elif dados.startswith(b"\xff\xd8\xff"):
        mime, ext = "image/jpeg", ".jpg"
    else:
        mime, ext = "image/webp", ".webp"
    corpo = {"base64Data": f"data:{mime};base64,{base64.b64encode(dados).decode()}",
             "uploadPath": "maquina", "fileName": f"{uuid.uuid4().hex}{ext}"}
    try:
        d = _checar(_requisitar(UPLOAD, chave, corpo))["data"]
        url = d.get("fileUrl") or d.get("downloadUrl")
    except (KeyError, TypeError, AttributeError) as e:
        raise KieErro(INESPERADA) from e
    if not isinstance(url, str) or not url.startswith("http"):
        raise KieErro(INESPERADA)
    return url


def _baixar_imagem(url: str, destino: Path, validar=None, erro: str = "") -> Path:
    destino = Path(destino)
    tmp = destino.with_name(f".{destino.name}.baixando")
    try:
        baixar(url, tmp)
        if not _e_imagem(tmp):
            raise KieErro("A KIE devolveu um arquivo que não é imagem.")
        if validar is not None and not validar(tmp.read_bytes()):
            raise KieErro(erro or "A KIE devolveu uma imagem inesperada.")
        os.replace(tmp, destino)
    finally:
        if tmp.exists():
            tmp.unlink()
    return destino


def gerar_imagem_url(chave: str, prompt: str, proporcao: str, referencias: "list[str] | None" = None,
                     modelo: str = "nano-banana-2", limite: float = 150) -> str:
    entrada = {"prompt": prompt, "aspect_ratio": proporcao, "output_format": "png"}
    if referencias:
        entrada["image_input"] = list(referencias)[:10]
    tid = criar_tarefa(chave, modelo, entrada)
    resultado = aguardar(chave, tid, intervalo=5, limite=limite)
    urls = resultado.get("resultUrls") if isinstance(resultado, dict) else None
    if not urls:
        raise KieErro("A KIE terminou mas não devolveu a imagem. Tente de novo.")
    return urls[0]


def gerar_imagem(chave: str, prompt: str, proporcao: str, destino: Path, modelo: str = "nano-banana-2",
                 limite: float = 150, referencias: "list[str] | None" = None) -> Path:
    url = gerar_imagem_url(chave, prompt, proporcao, referencias=referencias, modelo=modelo, limite=limite)
    return _baixar_imagem(url, destino)


def remover_fundo(chave: str, url_imagem: str, destino: Path, limite: float = 120) -> Path:
    """Recraft (na KIE) tira o fundo; o PNG só é aceito se tiver alfa e os cantos transparentes."""
    tid = criar_tarefa(chave, MODELO_SEM_FUNDO, {"image": url_imagem})
    resultado = aguardar(chave, tid, intervalo=3, limite=limite)
    urls = resultado.get("resultUrls") if isinstance(resultado, dict) else None
    if not urls:
        raise KieErro("A KIE terminou mas não devolveu a imagem sem fundo. Tente de novo.")
    return _baixar_imagem(urls[0], destino,
                          validar=lambda b: png.tem_alfa(b) and png.cantos_transparentes(b),
                          erro="A KIE devolveu a imagem sem fundo transparente.")
