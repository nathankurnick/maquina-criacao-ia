# tests/test_funil_dados.py
import json

import pytest

import funil_dados as fd


@pytest.mark.parametrize("entrada,esperado", [
    (27, 27.0), (9.9, 9.9), ("R$ 27,90", 27.9), ("27.90", 27.9), ("1.297,00", 1297.0), ("R$97", 97.0),
])
def test_preco(entrada, esperado):
    assert fd.preco(entrada) == pytest.approx(esperado)


@pytest.mark.parametrize("ruim", ["", "grátis", 0, -5, None, True, "R$"])
def test_preco_invalido(ruim):
    with pytest.raises(ValueError):
        fd.preco(ruim)


@pytest.mark.parametrize("entrada,esperado", [(0.3, 0.3), ("30%", 0.3), (30, 0.3), ("15", 0.15), (None, 0.225)])
def test_conversao(entrada, esperado):
    assert fd.conversao(entrada, "bump") == pytest.approx(esperado)


def test_conversao_padrao_e_invalida():
    assert fd.conversao(None, "upsell") == pytest.approx(0.15)
    with pytest.raises(ValueError):
        fd.conversao(150, "upsell")
    with pytest.raises(ValueError):
        fd.conversao("muito", "upsell")


def _gravar(tmp_path, dados):
    (tmp_path / "funil.json").write_text(json.dumps(dados), encoding="utf-8")
    return tmp_path


def _ler(tmp_path, dados):
    return fd.ler_funil(_gravar(tmp_path, dados))


def _bumps(conv=0.2, preco=9.9):
    return [{"nome": f"Bump {n}", "preco": preco, "conversao": conv} for n in range(1, 5)]


def test_ler_funil_completo_e_projecao(tmp_path):
    f = fd.ler_funil(_gravar(tmp_path, {
        "front": {"nome": "Front", "preco": 27},
        "bumps": _bumps(conv=0.3, preco=10),
        "upsell": {"nome": "Up", "preco": 67, "conversao": "15%"},
        "downsell": {"nome": "Down", "preco": 37, "conversao": 0.1}}))
    assert f["front"] == {"nome": "Front", "preco": 27.0}
    assert f["upsell"]["conversao"] == pytest.approx(0.15)
    p = fd.projetar(f)
    esperado = 27 + 4 * 10 * 0.3 + 67 * 0.15 + 37 * 0.85 * 0.1
    assert p["ticket_medio"] == pytest.approx(esperado)
    assert p["aumento_pct"] == pytest.approx((esperado - 27) / 27 * 100)
    assert [x["etapa"] for x in p["partes"]] == ["front"] + ["bump"] * 4 + ["upsell", "downsell"]
    assert p["aumento_upsell_pct"] == pytest.approx(67 * 0.15 / 27 * 100)


def test_ler_funil_so_front(tmp_path):
    f = fd.ler_funil(_gravar(tmp_path, {"front": {"nome": "F", "preco": "R$ 19,90"}, "bumps": _bumps()}))
    assert len(f["bumps"]) == 4 and f["upsell"] is None and f["downsell"] is None
    assert fd.projetar(f)["aumento_pct"] == pytest.approx(4 * 9.9 * 0.2 / 19.9 * 100)
    assert fd.projetar(f)["aumento_upsell_pct"] == 0


def test_aumento_upsell_ignora_bump_e_downsell(tmp_path):
    f = fd.ler_funil(_gravar(tmp_path, {
        "front": {"nome": "F", "preco": 100}, "bumps": _bumps(conv=0.4, preco=50),
        "upsell": {"nome": "U", "preco": 250, "conversao": 0.1},
        "downsell": {"nome": "D", "preco": 100, "conversao": 0.2}}))
    p = fd.projetar(f)
    assert p["aumento_upsell_pct"] == pytest.approx(25.0)
    assert p["aumento_pct"] > p["aumento_upsell_pct"]


@pytest.mark.parametrize("dados,trecho", [
    ({}, "front"),
    ({"front": {"nome": "F"}, "bumps": _bumps()}, "preco"),
    ({"front": {"nome": "F", "preco": 27}, "bumps": _bumps(), "downsell": {"nome": "D", "preco": 17}}, "downsell"),
    ({"front": {"nome": "F", "preco": 27}}, "4 order bumps"),
])
def test_ler_funil_erros(tmp_path, dados, trecho):
    with pytest.raises(ValueError, match=trecho):
        fd.ler_funil(_gravar(tmp_path, dados))


def test_arquivo_ausente_ou_quebrado(tmp_path):
    with pytest.raises(ValueError, match="funil.json"):
        fd.ler_funil(tmp_path)
    (tmp_path / "funil.json").write_text("{quebrado")
    with pytest.raises(ValueError, match="funil.json"):
        fd.ler_funil(tmp_path)


def test_brl():
    assert fd.brl(1234.5) == "R$ 1.234,50" and fd.brl(9.9) == "R$ 9,90" and fd.brl(27) == "R$ 27,00"


def test_conversao_um_ambiguo():
    for ruim in (1, "1"):
        with pytest.raises(ValueError, match="ambígua"):
            fd.conversao(ruim, "bump")
    assert fd.conversao("1%", "bump") == pytest.approx(0.01)
    assert fd.conversao("100%", "bump") == pytest.approx(1.0)
    assert fd.conversao(1.0, "bump") == pytest.approx(1.0)
    assert fd.conversao("0,3", "bump") == pytest.approx(0.3)
    assert fd.conversao(30, "bump") == pytest.approx(0.3)


def test_quatro_bumps_somam_no_ticket(tmp_path):
    f = _ler(tmp_path, {"front": {"nome": "F", "preco": 100}, "bumps": _bumps(conv=0.2, preco=10)})
    assert len(f["bumps"]) == 4 and "bump" not in f
    p = fd.projetar(f)
    assert [x["etapa"] for x in p["partes"]] == ["front"] + ["bump"] * 4
    assert p["ticket_medio"] == pytest.approx(100 + 4 * 10 * 0.2)


@pytest.mark.parametrize("bumps,trecho", [
    (None, "4 order bumps"),
    ([{"nome": "A", "preco": 9}] * 3, "4 order bumps"),
    ([{"nome": f"B{n}", "preco": 9} for n in range(5)], "4 order bumps"),
    ([{"nome": "Igual", "preco": 9}, {"nome": "igual", "preco": 9}, {"nome": "C", "preco": 9}, {"nome": "D", "preco": 9}],
     "diferentes"),
    ([{"nome": "A", "preco": 9}, {"nome": "B", "preco": 9}, {"nome": "C", "preco": 9}, {"preco": 9}], "bump 4"),
])
def test_bumps_invalidos(tmp_path, bumps, trecho):
    dados = {"front": {"nome": "F", "preco": 27}}
    if bumps is not None:
        dados["bumps"] = bumps
    with pytest.raises(ValueError, match=trecho):
        _ler(tmp_path, dados)


def test_formato_antigo_explica_a_troca(tmp_path):
    with pytest.raises(ValueError, match='troque "bump" por "bumps"'):
        _ler(tmp_path, {"front": {"nome": "F", "preco": 27}, "bump": {"nome": "B", "preco": 9}})


def test_conversao_padrao_do_bump_e_o_meio_da_nova_faixa(tmp_path):
    f = _ler(tmp_path, {"front": {"nome": "F", "preco": 27}, "bumps": [{"nome": f"B{n}", "preco": 9} for n in range(4)]})
    assert all(b["conversao"] == pytest.approx(0.225) for b in f["bumps"])
