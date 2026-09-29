import json
import os
import re
import stat
import subprocess
import zipfile
from pathlib import Path

import pytest

from entregavel_md import converter

RAIZ = Path(__file__).resolve().parent.parent
COMMAND = RAIZ / "Instalar Máquina.command"


def test_command_existe_e_executavel():
    assert COMMAND.exists()
    assert COMMAND.stat().st_mode & stat.S_IXUSR
    texto = COMMAND.read_text(encoding="utf-8")
    assert texto.startswith("#!/bin/bash")
    assert 'bash "$AQUI/instalar.sh"' in texto and "read" in texto


def test_command_roda_o_instalador_da_propria_pasta(tmp_path):
    pasta = tmp_path / "Máquina Criação IA"
    pasta.mkdir()
    (pasta / "Instalar Máquina.command").write_text(COMMAND.read_text(encoding="utf-8"), encoding="utf-8")
    (pasta / "instalar.sh").write_text('echo "rodou em $PWD com $0"\n', encoding="utf-8")
    r = subprocess.run(["bash", str(pasta / "Instalar Máquina.command")], input="\n",
                       capture_output=True, text=True)
    assert r.returncode == 0 and "rodou" in r.stdout


def test_leia_me():
    texto = (RAIZ / "LEIA-ME.txt").read_text(encoding="utf-8")
    assert "Instalar Máquina.command" in texto and "COMO-INSTALAR.pdf" in texto
    assert "botão direito" in texto and "Abrir" in texto


def test_guia_de_instalacao_no_formato_do_03():
    pasta = RAIZ / "docs-aluno" / "como-instalar"
    meta = json.loads((pasta / "meta.json").read_text(encoding="utf-8"))
    assert meta["tipo"] == "guia" and meta["titulo"]
    html, titulos = converter((pasta / "conteudo.md").read_text(encoding="utf-8"))
    nomes = " ".join(t["texto"] for t in titulos)
    for trecho in ("Claude Code", "Python", "chaves", "atualizar", "problema"):
        assert trecho.lower() in nomes.lower() or trecho.lower() in html.lower(), trecho
