"""Onde a Máquina guarda as coisas. Tudo sobrescrevível por env (testes)."""
import os
from pathlib import Path


def maquina_home() -> Path:
    return Path(os.environ.get("MAQUINA_HOME") or Path.home() / ".maquina")


def pasta_projetos() -> Path:
    return Path(os.environ.get("MAQUINA_PROJETOS") or Path.home() / "MaquinaIA")
