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


@pytest.mark.parametrize("entrada,esperado", [(0.3, 0.3), ("30%", 0.3), (30, 0.3), ("15", 0.15), (None, 0.30)])
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


def test_ler_funil_completo_e_projecao(tmp_path):
    f = fd.ler_funil(_gravar(tmp_path, {
        "front": {"nome": "Front", "preco": 27},
        "bump": {"nome": "Bump", "preco": 10, "conversao": 0.3},
        "upsell": {"nome": "Up", "preco": 67, "conversao": "15%"},
        "downsell": {"nome": "Down", "preco": 37, "conversao": 0.1}}))
    assert f["front"] == {"nome": "Front", "preco": 27.0}
    assert f["upsell"]["conversao"] == pytest.approx(0.15)
    p = fd.projetar(f)
    esperado = 27 + 10 * 0.3 + 67 * 0.15 + 37 * 0.85 * 0.1
    assert p["ticket_medio"] == pytest.approx(esperado)
    assert p["aumento_pct"] == pytest.approx((esperado - 27) / 27 * 100)
    assert [x["etapa"] for x in p["partes"]] == ["front", "bump", "upsell", "downsell"]


def test_ler_funil_so_front(tmp_path):
    f = fd.ler_funil(_gravar(tmp_path, {"front": {"nome": "F", "preco": "R$ 19,90"}}))
    assert f["bump"] is None and f["upsell"] is None and f["downsell"] is None
    assert fd.projetar(f)["aumento_pct"] == 0


@pytest.mark.parametrize("dados,trecho", [
    ({}, "front"),
    ({"front": {"nome": "F"}}, "preco"),
    ({"front": {"nome": "F", "preco": 27}, "downsell": {"nome": "D", "preco": 17}}, "downsell"),
    ({"front": {"nome": "F", "preco": 27}, "bump": {"preco": 9}}, "nome"),
    ({"front": {"nome": "F", "preco": 27}, "bump": "sim"}, "bump"),
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
