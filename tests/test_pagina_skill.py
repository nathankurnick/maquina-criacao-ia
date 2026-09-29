import json
import re
from pathlib import Path

import yaml

import pagina_conteudo as pc

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "02-pagina-de-vendas"


def _texto():
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def test_frontmatter():
    m = re.match(r"^---\n(.*?)\n---\n", _texto(), re.S)
    fm = yaml.safe_load(m.group(1))
    assert fm["name"] == "02-pagina-de-vendas" and len(fm["description"]) > 80


def test_referencias_existem():
    t = _texto()
    for rel in re.findall(r"`((?:scripts|referencias|template)/[\w.-]+)`", t):
        assert (SKILL / rel).exists(), rel
    for s in ("pagina_render.py", "pagina_config.py", "pagina_publicar.py"):
        assert f"scripts/{s}" in t


def test_comandos_autocontidos_e_aspas_simples():
    t = _texto()
    for bloco in re.findall(r"```bash\n(.*?)```", t, re.S):
        for linha in bloco.splitlines():
            for var in ("PY", "S", "M"):
                if f'"${var}"' in linha:
                    assert f"{var}=" in linha.split(f'"${var}"')[0], linha
            assert 'definir' not in linha or '="' not in linha.split("definir", 1)[1], linha


def test_regras_essenciais_no_texto():
    t = _texto()
    assert "maquina oferta mostrar" in t and "conteudo.json" in t
    assert "depoimento" in t.lower() and "real" in t.lower()
    assert "app.netlify.com/drop" in t or "saída 3" in t.lower()


def test_exemplo_da_referencia_e_um_conteudo_valido():
    ref = (SKILL / "referencias" / "copy.md").read_text(encoding="utf-8")
    bloco = re.search(r"```json\n(.*?)```", ref, re.S).group(1)
    conteudo, avisos = pc.normalizar(json.loads(bloco))
    assert conteudo["hero"]["ativo"]
    assert json.loads(bloco)["planos"]["basico"]["checkoutUrl"] == ""
    assert not [a for a in avisos if not a.startswith(("depoimentos", "carrossel", "planos: falta o link"))]
    assert any(a.startswith("planos: falta o link") for a in avisos)


def test_exemplo_nao_traz_dominio_de_checkout_de_mentira():
    ref = (SKILL / "referencias" / "copy.md").read_text(encoding="utf-8")
    bloco = re.search(r"```json\n(.*?)```", ref, re.S).group(1)
    for dominio in ("pay.kiwify.com.br/", "kiwify", "hotmart", "payt", "SEU-LINK"):
        assert dominio.lower() not in bloco.lower(), dominio


def test_skill_cobre_endereco_paleta_e_head():
    t = _texto()
    assert "--definir 'url=" in t and "endereço NOVO" in t and "maquina chaves" in t
    assert "oferta definir <slug> paleta='<escolhida>'" in t
    assert "<P>/pagina/head.html" in t and 'open "<P>/pagina"' in t
    assert "remonta a página antes" in t and "link_checkout" in t and "planos.basico.checkoutUrl" in t
