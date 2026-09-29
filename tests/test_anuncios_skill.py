import json
import re
from pathlib import Path

import yaml

import anuncio_dados

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "04-anuncios"


def _texto():
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def test_frontmatter():
    fm = yaml.safe_load(re.match(r"^---\n(.*?)\n---\n", _texto(), re.S).group(1))
    assert fm["name"] == "04-anuncios" and len(fm["description"]) > 80


def test_referencias_e_scripts():
    t = _texto()
    for rel in re.findall(r"`((?:scripts|referencias|template)/[\w.-]+)`", t):
        assert (SKILL / rel).exists(), rel
    for s in ("anuncio_riscos.py", "anuncio_criativo.py", "anuncio_exportar.py"):
        assert f"scripts/{s}" in t


def test_comandos_autocontidos():
    blocos = re.findall(r"```bash\n(.*?)```", _texto(), re.S)
    assert blocos
    for bloco in blocos:
        for linha in bloco.splitlines():
            for var in ("PY", "S", "M", "S1"):
                if f'"${var}"' in linha or f'"${var}/' in linha:
                    antes = re.split(rf'"\${var}[/"]', linha)[0]
                    assert f"{var}=" in antes, linha


def test_regras_no_texto():
    t = _texto().lower()
    assert "maquina oferta mostrar" in t and "anuncios.json" in t
    assert "aviso" in t and "grátis" in t and "aprova" in t and "timeout" in t


def test_comportamento_real_dos_scripts_no_texto():
    t = _texto()
    assert "--gerar-arte" in t and "600000" in t and "--id" in t
    assert "exit 2" in t or "código 2" in t
    assert "nova" in t.lower() and "pesquisa" in t
    assert "config.json" in t and "azul-laranja" in t
    assert "zonas seguras" in t.lower() or "safe zone" in t.lower()


def test_exemplo_do_anuncios_json_na_referencia_e_valido(tmp_path):
    ref = (SKILL / "referencias" / "angulos.md").read_text(encoding="utf-8")
    exemplo = re.search(r"```json\n(.*?)```", ref, re.S).group(1)
    json.loads(exemplo)
    (tmp_path / "anuncios.json").write_text(exemplo, encoding="utf-8")
    anuncios = anuncio_dados.ler_anuncios(tmp_path)
    assert {a["formato"] for a in anuncios} == {"estatico", "video"}
