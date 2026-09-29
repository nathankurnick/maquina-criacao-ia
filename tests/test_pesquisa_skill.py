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
    for script in ("raspar.py", "ofertas.py", "capturar.py", "baixar_criativos.py", "registrar_escolha.py"):
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


def test_skill_md_comandos_bash_autocontidos():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "PFX" not in texto
    for bloco in re.findall(r"```bash\n(.*?)```", texto, re.S):
        for linha in bloco.splitlines():
            for var in ("PY", "S", "M"):
                m = re.search(r'\$\{?%s\b' % var, linha)
                if m:
                    assert re.search(r'(^|[\s;])%s=' % var, linha[:m.start()]), linha


def test_skill_md_comandos_inline_autocontidos():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    texto = re.sub(r"```.*?```", "", texto, flags=re.S)
    for cmd in (c for c in re.findall(r"`([^`\n]+)`", texto) if " " in c.strip()):
        for var in ("PY", "S", "M"):
            m = re.search(r'"\$%s\b' % var, cmd)
            if m:
                assert re.search(r'(^|[\s;])%s=' % var, cmd[:m.start()]), cmd


def test_skill_cobre_escolha_criativos_checkout_e_saida_2():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for trecho in ("escolhida.json", "criativos.json", "links_checkout", "<O>/checkout",
                   "código 2", "oferta-whatsapp-pagina-agil", "REFERÊNCIA"):
        assert trecho in texto, trecho
    dissecacao = (SKILL / "referencias" / "dissecacao.md").read_text(encoding="utf-8")
    assert "**Busca:**" in dissecacao and "**Chave:**" in dissecacao and "REFERÊNCIA" in dissecacao


def test_nomes_de_modulo_dos_scripts_sao_unicos_entre_skills():
    nomes = [p.name for p in (RAIZ / "skills").glob("*/scripts/*.py")]
    assert len(nomes) == len(set(nomes))
    doc = (RAIZ / "nucleo" / "COMO-USAR-NAS-SKILLS.md").read_text(encoding="utf-8")
    for n in ("coleta", "raspar", "ofertas", "capturar", "baixar_criativos", "registrar_escolha"):
        assert f"`{n}`" in doc
