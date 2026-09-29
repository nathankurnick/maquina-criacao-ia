import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "01-pesquisa-ofertas"


def _frontmatter(texto):
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    assert m, "SKILL.md precisa começar com frontmatter YAML"
    return yaml.safe_load(m.group(1))


def test_skill_md_tem_nome_e_descricao():
    fm = _frontmatter((SKILL / "SKILL.md").read_text(encoding="utf-8"))
    assert fm["name"] == "01-pesquisa-ofertas"
    assert len(fm["description"]) > 80


def test_skill_md_referencia_arquivos_que_existem():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for rel in re.findall(r"`((?:scripts|referencias)/[\w.-]+)`", texto):
        assert (SKILL / rel).exists(), rel
    for script in ("raspar.py", "ofertas.py", "capturar.py"):
        assert f"scripts/{script}" in texto


def test_skill_md_nunca_manda_escrever_yaml_a_mao():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "maquina oferta definir" in texto and "maquina oferta adicionar" in texto
    assert "oferta.md" in texto


def test_instalador_copia_skill_sem_pycache(tmp_path):
    src = tmp_path / "skills_src"
    shutil.copytree(SKILL.parent, src, ignore=shutil.ignore_patterns("__pycache__"))
    (src / SKILL.name / "scripts" / "__pycache__").mkdir(exist_ok=True)
    binfake = tmp_path / "bin"
    binfake.mkdir()
    (binfake / "python3.12").symlink_to(sys.executable)
    (binfake / "claude").write_text("#!/bin/sh\nexit 0\n")
    (binfake / "claude").chmod(0o755)
    casa = tmp_path / "casa"
    env = {"HOME": str(casa), "PATH": f"{binfake}:/usr/bin:/bin",
           "MAQUINA_HOME": str(casa / ".maquina"), "MAQUINA_BIN": str(casa / "b"),
           "CLAUDE_SKILLS_DIR": str(casa / "skills"), "MAQUINA_PULAR_DEPS": "1", "MAQUINA_SKILLS_SRC": str(src), "MAQUINA_PY_DIRS": ""}
    r = subprocess.run(["bash", str(RAIZ / "instalar.sh"), "--sem-chaves"], env=env,
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
    destino = casa / "skills" / "01-pesquisa-ofertas"
    assert (destino / "SKILL.md").exists()
    assert (destino / "scripts" / "raspar.py").exists()
    assert not list(destino.rglob("__pycache__"))
