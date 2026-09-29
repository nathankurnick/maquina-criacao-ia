"""Erros com mensagem pronta pro aluno + log técnico separado."""
from datetime import datetime
from pathlib import Path

from nucleo.caminhos import maquina_home


class MaquinaErro(Exception):
    """Erro cuja mensagem já está em português e diz o próximo passo."""


def registrar_log(texto: str) -> Path:
    pasta = maquina_home() / "log"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "maquina.log"
    with arquivo.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {texto}\n")
    return arquivo
