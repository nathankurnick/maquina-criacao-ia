"""Publica uma pasta estática na conta Netlify do aluno."""
import http.client
import io
import json
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from nucleo.erros import MaquinaErro

BASE = "https://api.netlify.com/api/v1"
INESPERADA = "A Netlify devolveu uma resposta inesperada. Tente de novo em alguns minutos."
URL_TOKEN = "https://app.netlify.com/user/applications#personal-access-tokens"


class NetlifyErro(MaquinaErro):
    pass


def _requisitar(metodo: str, caminho: str, token: str, corpo: "bytes | None" = None,
                tipo: str = "application/json") -> dict:
    req = urllib.request.Request(
        f"{BASE}{caminho}", data=corpo, method=metodo,
        headers={"Authorization": f"Bearer {token}", "Content-Type": tipo},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            dados = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise NetlifyErro(f"A Netlify recusou o token. Gere outro em {URL_TOKEN} e rode: maquina chaves") from e
        if e.code == 429:
            raise NetlifyErro("A Netlify recebeu muitas requisições. Espere um minuto e tente de novo.") from e
        raise NetlifyErro(f"A Netlify respondeu com erro {e.code}. Tente de novo em alguns minutos.") from e
    except (OSError, http.client.HTTPException) as e:  # URLError e TimeoutError são OSError
        raise NetlifyErro("Não consegui falar com a Netlify. Confira sua internet e tente de novo.") from e
    except ValueError as e:  # corpo não é JSON
        raise NetlifyErro(INESPERADA) from e
    if not isinstance(dados, dict):
        raise NetlifyErro(INESPERADA)
    return dados


def validar(token: str) -> str:
    u = _requisitar("GET", "/user", token)
    return u.get("email") or u.get("full_name") or "conta ok"


def _zipar(pasta: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(pasta.rglob("*")):
            if arq.is_file() and not arq.name.startswith("."):
                z.write(arq, arq.relative_to(pasta).as_posix())
    return buf.getvalue()


def publicar_pasta(token: str, pasta: Path, site_id: "str | None" = None) -> dict:
    if not (pasta / "index.html").exists():
        raise NetlifyErro(f"Não achei o index.html em {pasta}. Gere a página antes de publicar.")
    if not site_id:
        site_id = _requisitar("POST", "/sites", token, b"{}").get("id")
        if not site_id:
            raise NetlifyErro(INESPERADA)
    deploy = _requisitar("POST", f"/sites/{site_id}/deploys", token, _zipar(pasta), "application/zip")
    return {"site_id": site_id, "url": deploy.get("ssl_url") or deploy.get("url")}
