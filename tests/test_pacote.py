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
    assert "Privacidade e Segurança" in texto and "Abrir Mesmo Assim" in texto
    assert "botão direito" in texto and "Abrir" in texto


def test_guia_de_instalacao_no_formato_do_03():
    pasta = RAIZ / "docs-aluno" / "como-instalar"
    meta = json.loads((pasta / "meta.json").read_text(encoding="utf-8"))
    assert meta["tipo"] == "guia" and meta["titulo"]
    html, titulos = converter((pasta / "conteudo.md").read_text(encoding="utf-8"))
    nomes = " ".join(t["texto"] for t in titulos)
    for trecho in ("Claude Code", "Python", "chaves", "atualizar", "problema"):
        assert trecho.lower() in nomes.lower() or trecho.lower() in html.lower(), trecho


def _empacotar(tmp_path):
    copia = tmp_path / "repo"
    subprocess.run(["rsync", "-a", "--exclude", ".venv", "--exclude", "dist", f"{RAIZ}/", f"{copia}/"], check=True)
    (copia / "tests" / "__pycache__").mkdir(parents=True, exist_ok=True)
    (copia / "skills" / "01-pesquisa-ofertas" / "scripts" / "__pycache__").mkdir(exist_ok=True)
    (copia / ".DS_Store").write_text("x")
    r = subprocess.run(["bash", str(copia / "dev" / "empacotar.sh"), "--sem-pdf"], cwd=copia,
                       capture_output=True, text=True)
    return r, copia


def test_empacotar_gera_zip_limpo_com_permissoes(tmp_path):
    r, copia = _empacotar(tmp_path)
    assert r.returncode == 0, r.stderr
    versao = (copia / "VERSION").read_text().strip()
    zip_arq = copia / "dist" / f"maquina-criacao-ia-{versao}.zip"
    assert zip_arq.exists() and str(zip_arq) in r.stdout
    z = zipfile.ZipFile(zip_arq)
    nomes = z.namelist()
    raiz = f"maquina-criacao-ia-{versao}/"
    for obrigatorio in ("instalar.sh", "Instalar Máquina.command", "LEIA-ME.txt", "INSTALAR-COM-CLAUDE.md", "VERSION", "requirements.txt",
                        "bin/maquina", "nucleo/cli.py", "skills/05-funil/SKILL.md"):
        assert raiz + obrigatorio in nomes, obrigatorio
    for proibido in ("tests/", ".venv", "__pycache__", "/dev/", "docs-aluno/", "/log/", ".DS_Store",
                     "requirements-dev.txt", "pytest.ini"):
        assert not [n for n in nomes if proibido in n], proibido
    for executavel in ("instalar.sh", "Instalar Máquina.command", "bin/maquina"):
        modo = z.getinfo(raiz + executavel).external_attr >> 16
        assert modo & stat.S_IXUSR, executavel


def test_empacotar_com_pdf(tmp_path):
    pytest.importorskip("playwright")
    copia = tmp_path / "repo"
    # o openrsync do macOS trava ao copiar o .venv; o empacotador só precisa do python dele, então linkamos
    subprocess.run(["rsync", "-a", "--exclude", ".venv", "--exclude", "dist", f"{RAIZ}/", f"{copia}/"], check=True)
    (copia / ".venv").symlink_to(RAIZ / ".venv")
    r = subprocess.run(["bash", str(copia / "dev" / "empacotar.sh")], cwd=copia, capture_output=True, text=True)
    if r.returncode != 0 and "Executable doesn't exist" in (r.stdout + r.stderr):
        pytest.skip("Chromium do Playwright não instalado")
    assert r.returncode == 0, r.stdout + r.stderr
    versao = (copia / "VERSION").read_text().strip()
    z = zipfile.ZipFile(copia / "dist" / f"maquina-criacao-ia-{versao}.zip")
    pdf = z.read(f"maquina-criacao-ia-{versao}/COMO-INSTALAR.pdf")
    assert pdf[:4] == b"%PDF"
