import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _rodar(tmp_path, com_claude=True, com_python=True, args=("--sem-chaves",), stdin=None, extra_env=None):
    binfake = tmp_path / "binfake"
    binfake.mkdir(exist_ok=True)
    (binfake / "python3.12").unlink(missing_ok=True)
    if com_python:
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
        "MAQUINA_PY_DIRS": "",
        **(extra_env or {}),
    }
    r = subprocess.run(["bash", str(RAIZ / "instalar.sh"), *args],
                       env=env, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL if stdin is None else None,
                       input=stdin)
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
    origem = tmp_path / "skills-src"
    (origem / "zz-teste").mkdir(parents=True)
    (origem / "zz-teste" / "SKILL.md").write_text("---\nname: zz-teste\n---\n")
    (origem / "sem-skill-md").mkdir()
    _, home, _ = _rodar(tmp_path, extra_env={"MAQUINA_SKILLS_SRC": str(origem)})
    assert (home / ".claude" / "skills" / "zz-teste" / "SKILL.md").exists()
    assert not (home / ".claude" / "skills" / "sem-skill-md").exists()


def test_chaves_falhando_nao_derruba_instalacao(tmp_path):
    r, _, _ = _rodar(tmp_path, args=())
    assert r.returncode == 0, r.stderr
    assert "instalada" in r.stdout
    assert "Sem problema" in r.stdout + r.stderr


def test_sem_python_moderno_para_com_mensagem(tmp_path):
    r, _, _ = _rodar(tmp_path, com_python=False)
    assert r.returncode == 1
    assert "Python 3.10" in r.stderr


def test_opcao_desconhecida_avisa_e_continua(tmp_path):
    r, _, _ = _rodar(tmp_path, args=("--sem-chaves", "--foo"))
    assert r.returncode == 0, r.stderr
    assert "Opção desconhecida: --foo" in r.stderr


def test_venv_velho_e_recriado(tmp_path):
    _, home, _ = _rodar(tmp_path)
    py = home / ".maquina" / "venv" / "bin" / "python"
    py.unlink()
    py.write_text("#!/bin/sh\nexit 1\n")
    py.chmod(0o755)
    r, _, _ = _rodar(tmp_path)
    assert r.returncode == 0, r.stderr
    ok = subprocess.run([str(py), "-c", "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"])
    assert ok.returncode == 0


def test_reinstalar_duas_vezes_uma_linha_no_zshrc_e_preserva_projetos(tmp_path):
    _, home, _ = _rodar(tmp_path)
    proj = home / "MaquinaIA" / "x"
    proj.mkdir(parents=True)
    (proj / "arq.txt").write_text("oi")
    r, _, _ = _rodar(tmp_path)
    assert r.returncode == 0, r.stderr
    zshrc = (home / ".zshrc").read_text()
    assert zshrc.count("MAQUINA_BIN_PATH") == 1
    assert (proj / "arq.txt").read_text() == "oi"


def test_maquina_ignora_pasta_atual_com_nucleo_falso(tmp_path):
    _, home, env = _rodar(tmp_path)
    falso = tmp_path / "aluno"
    (falso / "nucleo").mkdir(parents=True)
    (falso / "nucleo" / "__init__.py").write_text("")
    (falso / "nucleo" / "cli.py").write_text("def main():\n    print('FALSO')\n    return 0\n")
    r = subprocess.run([str(home / "bin" / "maquina"), "versao"], env=env, cwd=falso,
                       capture_output=True, text=True)
    assert "FALSO" not in r.stdout
    assert r.stdout.strip() == (RAIZ / "VERSION").read_text().strip()


def test_maquina_repassa_argumentos(tmp_path):
    _, home, env = _rodar(tmp_path)
    r = subprocess.run([str(home / "bin" / "maquina"), "isso-nao-existe", "--x"], env=env,
                       capture_output=True, text=True)
    assert r.returncode == 2
    assert "Comando inválido" in r.stderr and "isso-nao-existe" in r.stderr


def test_instalador_mostra_versao_e_os_5_sistemas(tmp_path):
    r, _, _ = _rodar(tmp_path)
    assert r.returncode == 0, r.stderr
    versao = (RAIZ / "VERSION").read_text().strip()
    assert f"Versão {versao}" in r.stdout
    for s in ("/01-pesquisa-ofertas", "/02-pagina-de-vendas", "/03-entregaveis", "/04-anuncios", "/05-funil"):
        assert s in r.stdout
