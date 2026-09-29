"""Chaves de API do aluno em ~/.maquina/chaves.env (600)."""
import os
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


def salvar_chave(nome: str, valor: str) -> None:
    if nome not in CHAVES:
        raise MaquinaErro(f"Chave desconhecida: {nome}")
    dados = ler_chaves()
    dados[nome] = valor.strip()
    arq = arquivo_chaves()
    arq.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(arq.parent, 0o700)
    arq.touch(mode=0o600, exist_ok=True)
    os.chmod(arq, 0o600)
    arq.write_text("".join(f"{k}={v}\n" for k, v in dados.items()), encoding="utf-8")


def obter_chave(nome: str) -> "str | None":
    return os.environ.get(nome) or ler_chaves().get(nome) or None


def testar_chave(nome: str, valor: str) -> str:
    if nome not in _VALIDADORES:
        raise MaquinaErro(f"Chave desconhecida: {nome}")
    return _VALIDADORES[nome](valor)
