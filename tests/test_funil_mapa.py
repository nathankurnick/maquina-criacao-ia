# tests/test_funil_mapa.py
import json

import pytest

import funil_dados as fd
import funil_mapa as fm


def _funil(**troca):
    base = {"front": {"nome": "Marmitas <Já>", "preco": 27},
            "bump": {"nome": "Lista", "preco": 9.9, "conversao": 0.3},
            "upsell": {"nome": "Cardápio 30", "preco": 67, "conversao": 0.15},
            "downsell": {"nome": "Cardápio 15", "preco": 37, "conversao": 0.15}}
    base.update(troca)
    return base


def _ler(tmp_path, dados):
    (tmp_path / "funil.json").write_text(json.dumps(dados), encoding="utf-8")
    return fd.ler_funil(tmp_path)


def test_html_mapa_completo(tmp_path):
    f = _ler(tmp_path, _funil())
    h = fm.html_mapa(f, fd.projetar(f), "preto-dourado")
    assert "Marmitas &lt;Já&gt;" in h and "R$ 27,00" in h and "R$ 67,00" in h
    assert "Order bump" in h and "Upsell" in h and "Downsell" in h and "recusou" in h
    assert "referência: 20–40%" in h and "referência: 10–20%" in h
    assert "--pg-destaque:#d4af37" in h and "Área de membros" in h
    assert fd.brl(fd.projetar(f)["ticket_medio"]) in h


def test_meta_atingida_ou_nao(tmp_path):
    alto = _ler(tmp_path, _funil())
    assert "✅" in fm.html_mapa(alto, fd.projetar(alto), "azul-laranja")
    so_front = _ler(tmp_path, {"front": {"nome": "F", "preco": 27}})
    h = fm.html_mapa(so_front, fd.projetar(so_front), "azul-laranja")
    assert "⚠️" in h and "Upsell" not in h


def test_gerar_de_verdade(tmp_path):
    pytest.importorskip("playwright")
    p = tmp_path / "proj"
    (p / "funil").mkdir(parents=True)
    (p / "funil" / "funil.json").write_text(json.dumps(_funil()), encoding="utf-8")
    (p / "pagina").mkdir()
    (p / "pagina" / "config.json").write_text(json.dumps({"paleta": "verde-branco"}))
    try:
        r = fm.gerar(p)
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise
    png = r["png"].read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and int.from_bytes(png[16:20], "big") == 1080
    assert "--pg-destaque:#22c55e" in r["html"].read_text(encoding="utf-8")
    assert not [x for x in (p / "funil").iterdir() if x.name.startswith(".")]


def test_main_erros(tmp_path, capsys):
    assert fm.main(["--projeto", str(tmp_path)]) == 1
    assert "funil.json" in capsys.readouterr().err
    assert fm.main([]) == 1
    (tmp_path / "funil").mkdir()
    (tmp_path / "funil" / "funil.json").write_text(json.dumps(_funil()))
    assert fm.main(["--projeto", str(tmp_path), "--paleta", "rosa"]) == 1
    assert "azul-laranja" in capsys.readouterr().err


def _html(tmp_path, upsell_conv=0.15, bump_conv=0.3, preco_up=67):
    f = _ler(tmp_path, _funil(upsell={"nome": "U", "preco": preco_up, "conversao": upsell_conv},
                              bump={"nome": "B", "preco": 9.9, "conversao": bump_conv}))
    return fm.html_mapa(f, fd.projetar(f), "azul-laranja")


def test_faixas_do_resumo(tmp_path):
    baixo = _ler(tmp_path, {"front": {"nome": "F", "preco": 100}, "bump": {"nome": "B", "preco": 10, "conversao": 0.3}})
    assert "⚠️ abaixo da meta de 25–30%" in fm.html_mapa(baixo, fd.projetar(baixo), "azul-laranja")
    meio = _ler(tmp_path, {"front": {"nome": "F", "preco": 100}, "bump": {"nome": "B", "preco": 90, "conversao": 0.3}})
    h = fm.html_mapa(meio, fd.projetar(meio), "azul-laranja")
    assert "✅ dentro da meta de 25–30%" in h and "otimistas" not in h
    alto = _ler(tmp_path, _funil())
    h = fm.html_mapa(alto, fd.projetar(alto), "azul-laranja")
    assert "✅ acima da meta de 25–30%" in h and "confira se as conversões não estão otimistas" in h


def test_fora_da_referencia(tmp_path):
    assert "fora da referência" not in _html(tmp_path)
    h = _html(tmp_path, upsell_conv=0.5)
    assert h.count("fora da referência") == 1
    assert h.count("fora da referência") == _html(tmp_path, bump_conv=0.9).count("fora da referência")


def test_pct_abaixo_de_1():
    assert fm._pct(0.003) == "0,3%" and fm._pct(0.15) == "15%" and fm._pct(0) == "0%"


def test_paleta_da_oferta_md(tmp_path, monkeypatch):
    pytest.importorskip("playwright")
    p = tmp_path / "proj"
    (p / "funil").mkdir(parents=True)
    (p / "funil" / "funil.json").write_text(json.dumps(_funil()), encoding="utf-8")
    (p / "oferta.md").write_text("---\nnome: X\npaleta: verde-branco\n---\ncorpo\n", encoding="utf-8")
    assert fm._paleta_oferta(p) == "verde-branco"
    (p / "oferta.md").write_text("---\n: quebrado [\n---\n", encoding="utf-8")
    assert fm._paleta_oferta(p) == ""
    assert fm._paleta_oferta(tmp_path / "nada") == ""
