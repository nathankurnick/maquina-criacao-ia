import json
import re
from pathlib import Path

import yaml

import funil_dados

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "05-funil"


def _texto():
    return (SKILL / "SKILL.md").read_text(encoding="utf-8")


def test_frontmatter():
    fm = yaml.safe_load(re.match(r"^---\n(.*?)\n---\n", _texto(), re.S).group(1))
    assert fm["name"] == "05-funil" and len(fm["description"]) > 80


def test_referencias_e_scripts():
    t = _texto()
    for rel in re.findall(r"`((?:scripts|referencias|template)/[\w./-]+)`", t):
        assert (SKILL / rel).exists(), rel
    for s in ("funil_mapa.py", "funil_oto.py"):
        assert f"scripts/{s}" in t
    for ref in ("upsell/metodologia.md", "upsell/copy-5-blocos.md", "upsell/caso-exemplo.md",
                "order-bump.md", "mensagens.md", "plataformas.md"):
        assert (SKILL / "referencias" / ref).exists(), ref


def test_copias_do_metodo_sem_referencias_quebradas():
    for arq in (SKILL / "referencias" / "upsell").glob("*.md"):
        conteudo = arq.read_text(encoding="utf-8")
        assert "transcricoes/" not in conteudo and "exemplos-analisados/" not in conteudo, arq.name


def test_comandos_autocontidos():
    for bloco in re.findall(r"```bash\n(.*?)```", _texto(), re.S):
        for linha in bloco.splitlines():
            for var in ("PY", "S", "M"):
                if f'"${var}"' in linha or f'"${var}/' in linha:
                    antes = re.split(rf'"\${var}[/"]', linha)[0]
                    assert f"{var}=" in antes, linha


def test_regras_no_texto():
    t = _texto().lower()
    assert "maquina oferta mostrar" in t and "funil.json" in t and "oto.json" in t
    assert "checkpoint" in t or "aprova" in t
    assert "relato" in t and "real" in t
    assert "app.netlify.com/drop" in t or "saída 3" in t


def test_exemplo_do_funil_json_e_valido(tmp_path):
    exemplo = re.search(r"```json\n(\{.*?\"front\".*?)```", _texto(), re.S).group(1)
    (tmp_path / "funil.json").write_text(exemplo, encoding="utf-8")
    assert funil_dados.ler_funil(tmp_path)["upsell"]


def test_regras_novas_no_texto():
    t = _texto()
    for trecho in ("botao_no_player", "--definir-url", "recusar_url", "entregaveis/<item>",
                   "Fase 0", "Thumbnail", "confirme esta informação", "S3=", "DOWNSELL primeiro"):
        assert trecho in t, trecho
    assert not re.search(r"```bash\n[^`]*maquina oferta adicionar[^`]*funil", t)


def test_exemplo_do_upsell_dentro_da_meta(tmp_path):
    exemplo = re.search(r"```json\n(\{.*?\"front\".*?)```", _texto(), re.S).group(1)
    (tmp_path / "funil.json").write_text(exemplo, encoding="utf-8")
    f = funil_dados.ler_funil(tmp_path)
    p = funil_dados.projetar(f)
    assert 25 <= p["aumento_upsell_pct"] <= 30
    assert f["upsell"]["preco"] >= 2.5 * f["front"]["preco"]


def test_exemplo_do_oto_json_e_valido(tmp_path):
    import funil_oto
    exemplo = re.search(r"```json\n(\{\"formato\".*?)```", _texto(), re.S).group(1)
    exemplo = exemplo.replace("<link do YouTube/Vimeo ou o código do player do VTurb>", "https://youtu.be/abcDEF12345") \
        .replace("<link de pagamento do upsell na plataforma>", "https://pay.x.com/up") \
        .replace("<link do downsell (publicado antes) ou da página de obrigado / área de membros>", "https://x.com/ok")
    (tmp_path / "oto.json").write_text(exemplo, encoding="utf-8")
    assert funil_oto.ler_oto(tmp_path)["atraso_segundos"] > 0


def test_mockup_do_oto_documentado():
    t = _texto()
    assert "--mockup" in t and '"entregavel"' in t


def test_quatro_bumps_no_skill():
    t = _texto()
    assert '"bumps"' in t and "4 order bumps" in t
    exemplo = json.loads(re.search(r"```json\n(\{\"front\".*?)```", t, re.S).group(1))
    assert len(exemplo["bumps"]) == 4
