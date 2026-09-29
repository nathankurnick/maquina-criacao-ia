# tests/test_entregaveis_skill.py
import re
from pathlib import Path

import yaml

from entregavel_md import converter

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "03-entregaveis"


def _texto():
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def test_frontmatter():
    fm = yaml.safe_load(re.match(r"^---\n(.*?)\n---\n", _texto(), re.S).group(1))
    assert fm["name"] == "03-entregaveis" and len(fm["description"]) > 80


def test_referencias_e_scripts_existem():
    t = _texto()
    for rel in re.findall(r"`((?:scripts|referencias|template)/[\w.-]+)`", t):
        assert (SKILL / rel).exists(), rel
    for s in ("entregavel_pdf.py", "entregavel_capa.py", "entregavel_planilha.py"):
        assert f"scripts/{s}" in t


def test_comandos_autocontidos():
    for bloco in re.findall(r"```bash\n(.*?)```", _texto(), re.S):
        for linha in bloco.splitlines():
            for var in ("PY", "S", "M", "S2"):
                if f'"${var}"' in linha or f'"${var}/' in linha:
                    antes = re.split(rf'"\${var}[/"]', linha)[0]
                    assert f"{var}=" in antes, linha
            if "oferta definir" in linha or "oferta adicionar" in linha:
                assert '="' not in linha.split("oferta", 1)[1], linha


def test_regras_no_texto():
    t = _texto()
    assert "maquina oferta mostrar" in t and "maquina oferta adicionar" in t
    assert "aprova" in t.lower() and "prova" in t.lower()
    assert "conteudo.md" in t and "meta.json" in t


def test_comportamento_real_dos_scripts():
    t = _texto()
    assert "300000" in t and "arte.png" in t and "pagina_render.py" in t
    assert "planilha.json" in t and "amostra-1.png" in t


def test_exemplo_de_markdown_da_referencia_converte():
    ref = (SKILL / "referencias" / "escrita.md").read_text(encoding="utf-8")
    exemplo = re.search(r"```markdown\n(.*?)```", ref, re.S).group(1)
    html, titulos = converter(exemplo)
    assert titulos and "caixa dica" in html and "checklist" in html and "<table>" in html
