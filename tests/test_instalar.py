import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _rodar(tmp_path, com_claude=True):
    binfake = tmp_path / "binfake"
    binfake.mkdir(exist_ok=True)
    (binfake / "python3.12").unlink(missing_ok=True)
    (binfake / "python3.12").symlink_to(sys.executable)
    claude = binfake / "claude"
    if com_claude:
        claude.write_text("#!/bin/sh\nexit 0\n")
        claude.chmod(0o755)
    elif claude.exists():
        claude.unlink()
    home = tmp_path / "casa"
    env = {
        "HOME": str(home),
        "PATH": f"{binfake}:/usr/bin:/bin",
        "MAQUINA_HOME": str(home / ".maquina"),
        "MAQUINA_BIN": str(home / "bin"),
        "CLAUDE_SKILLS_DIR": str(home / ".claude" / "skills"),
        "MAQUINA_PULAR_DEPS": "1",
    }
    r = subprocess.run(["bash", str(RAIZ / "instalar.sh"), "--sem-chaves"],
                       env=env, capture_output=True, text=True)
    return r, home, env


def test_sem_claude_para_com_mensagem(tmp_path):
    r, _, _ = _rodar(tmp_path, com_claude=False)
    assert r.returncode == 1
    assert "Claude Code" in r.stderr


def test_instala_e_maquina_responde(tmp_path):
    r, home, env = _rodar(tmp_path)
    assert r.returncode == 0, r.stderr
    assert (home / ".maquina" / "nucleo" / "cli.py").exists()
    assert (home / ".maquina" / "venv" / "bin" / "python").exists()
    assert oct((home / ".maquina").stat().st_mode & 0o777) == "0o700"
    versao = subprocess.run([str(home / "bin" / "maquina"), "versao"],
                            env=env, capture_output=True, text=True)
    assert versao.stdout.strip() == (RAIZ / "VERSION").read_text().strip()


def test_reinstalar_preserva_chaves(tmp_path):
    _, home, _ = _rodar(tmp_path)
    chaves = home / ".maquina" / "chaves.env"
    chaves.write_text("KIE_API_KEY=abc\n")
    r, _, _ = _rodar(tmp_path)
    assert r.returncode == 0, r.stderr
    assert chaves.read_text() == "KIE_API_KEY=abc\n"


def test_copia_skills_com_skill_md(tmp_path):
    skill = RAIZ / "skills" / "zz-teste"
    skill.mkdir()
    try:
        (skill / "SKILL.md").write_text("---\nname: zz-teste\n---\n")
        _, home, _ = _rodar(tmp_path)
        assert (home / ".claude" / "skills" / "zz-teste" / "SKILL.md").exists()
    finally:
        (skill / "SKILL.md").unlink()
        skill.rmdir()
