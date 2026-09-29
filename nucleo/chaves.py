"""Chaves de API do aluno em ~/.maquina/chaves.env (600)."""
import os
import re
import uuid
from pathlib import Path

from nucleo import kie, netlify
from nucleo.caminhos import maquina_home
from nucleo.erros import MaquinaErro

CHAVES = {
    "KIE_API_KEY": ("KIE", "gerar imagens de anúncios, capas e mockups", "https://kie.ai/api-key"),
    "NETLIFY_TOKEN": ("Netlify", "publicar suas páginas sozinho", netlify.URL_TOKEN),
}
_VALIDADORES = {"KIE_API_KEY": lambda v: kie.validar(v), "NETLIFY_TOKEN": lambda v: netlify.validar(v)}


def arquivo_chaves() -> Path:
    return maquina_home() / "chaves.env"


def ler_chaves() -> dict[str, str]:
    arq = arquivo_chaves()
    if not arq.exists():
        return {}
    dados = {}
    for linha in arq.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            dados[k.strip()] = v.strip()
    return dados


def validar_formato(valor: str) -> str:
    """Devolve a chave limpa ou levanta erro se tiver espaço/caractere invisível."""
    valor = (valor or "").strip()
    if not re.fullmatch(r"[\x21-\x7e]+", valor):
        raise MaquinaErro("Essa chave tem caracteres estranhos ou espaços — copie de novo direto do site.")
    return valor


def salvar_chave(nome: str, valor: str) -> None:
    if nome not in CHAVES:
        raise MaquinaErro(f"Chave desconhecida: {nome}")
    valor = validar_formato(valor)
    dados = ler_chaves()
    dados[nome] = valor
    arq = arquivo_chaves()
    arq.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(arq.parent, 0o700)
    tmp = arq.with_name(f".{arq.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("".join(f"{k}={v}\n" for k, v in dados.items()))
        os.replace(tmp, arq)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def obter_chave(nome: str) -> "str | None":
    return os.environ.get(nome) or ler_chaves().get(nome) or None


def testar_chave(nome: str, valor: str) -> str:
    if nome not in _VALIDADORES:
        raise MaquinaErro(f"Chave desconhecida: {nome}")
    return _VALIDADORES[nome](valor)
