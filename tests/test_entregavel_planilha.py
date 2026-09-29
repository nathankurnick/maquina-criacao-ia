# tests/test_entregavel_planilha.py
import json
import zipfile
import xml.etree.ElementTree as ET

import pytest

import entregavel_planilha as ep

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _abas():
    return [{"nome": "Cardápio: Semana 1?", "colunas": ["Dia", "Refeição", "Calorias"],
             "linhas": [["Seg", "Omelete & salada", 420], ["Ter", "Frango <grelhado>", 510.5],
                        ["Total", None, "=SUM(C2:C3)"]], "larguras": [12, 30, 12]},
            {"nome": "Cardápio: Semana 1?", "colunas": ["A"], "linhas": []}]


def test_gerar_xlsx_estrutura_e_celulas(tmp_path):
    arq = ep.gerar_xlsx(_abas(), tmp_path / "plano.xlsx")
    z = zipfile.ZipFile(arq)
    nomes = set(z.namelist())
    assert {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels",
            "xl/styles.xml", "xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"} <= nomes
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    abas = [s.get("name") for s in wb.find("m:sheets", NS)]
    assert abas == ["Cardápio Semana 1", "Cardápio Semana 1 (2)"]
    sh = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    celulas = {c.get("r"): c for c in sh.iter(f"{{{NS['m']}}}c")}
    assert celulas["A1"].get("s") == "1" and celulas["A1"].find("m:is/m:t", NS).text == "Dia"
    assert celulas["B2"].find("m:is/m:t", NS).text == "Omelete & salada"
    assert celulas["C2"].find("m:v", NS).text == "420" and celulas["C3"].find("m:v", NS).text == "510.5"
    assert celulas["C4"].find("m:f", NS).text == "SUM(C2:C3)"
    assert "B4" not in celulas
    assert sh.find("m:sheetViews/m:sheetView/m:pane", NS).get("state") == "frozen"
    assert [c.get("width") for c in sh.find("m:cols", NS)] == ["12", "30", "12"]


def test_coluna_depois_de_z():
    assert ep._coluna(1) == "A" and ep._coluna(26) == "Z" and ep._coluna(27) == "AA" and ep._coluna(703) == "AAA"


def test_ler_planilha_json_erros(tmp_path):
    with pytest.raises(ValueError, match="planilha.json"):
        ep.ler_planilha_json(tmp_path)
    (tmp_path / "planilha.json").write_text('{"abas": []}')
    with pytest.raises(ValueError, match="aba"):
        ep.ler_planilha_json(tmp_path)
    (tmp_path / "planilha.json").write_text('{"abas": [{"nome": "X", "colunas": "não é lista"}]}')
    with pytest.raises(ValueError, match="colunas"):
        ep.ler_planilha_json(tmp_path)


def test_main_ok_e_erro(tmp_path, capsys):
    pasta = tmp_path / "planner-semanal"
    pasta.mkdir()
    (pasta / "planilha.json").write_text(json.dumps({"abas": _abas()}), encoding="utf-8")
    assert ep.main(["--pasta", str(pasta)]) == 0
    assert (pasta / "planner-semanal.xlsx").exists()
    assert "planner-semanal.xlsx" in capsys.readouterr().out
    assert ep.main(["--pasta", str(tmp_path / "nada")]) == 1
    assert ep.main([]) == 1


def test_utf8_invalido_atomico_e_controle(tmp_path, capsys):
    pasta = tmp_path / "p"
    pasta.mkdir()
    (pasta / "planilha.json").write_bytes(b'{"abas": [{"nome": "\xe7", "colunas": []}]}')
    assert ep.main(["--pasta", str(pasta)]) == 1
    assert "UTF-8" in capsys.readouterr().err
    arq = ep.gerar_xlsx([{"nome": "A", "colunas": ["x\x01y"], "linhas": []}], tmp_path / "a.xlsx")
    assert b"\x01" not in zipfile.ZipFile(arq).read("xl/worksheets/sheet1.xml")
    assert not list(tmp_path.glob("*.tmp"))
