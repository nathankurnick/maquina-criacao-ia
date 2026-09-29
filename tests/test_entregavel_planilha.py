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


def test_calc_on_load_e_apostrofos(tmp_path):
    arq = ep.gerar_xlsx([{"nome": "'Plano'", "colunas": ["A"], "linhas": []},
                         {"nome": "'''", "colunas": ["A"], "linhas": []}], tmp_path / "a.xlsx")
    z = zipfile.ZipFile(arq)
    wb = z.read("xl/workbook.xml").decode()
    assert '</sheets><calcPr fullCalcOnLoad="1"/>' in wb
    assert [s.get("name") for s in ET.fromstring(wb).find("m:sheets", NS)] == ["Plano", "Planilha"]


def _escreve(pasta, abas):
    pasta.mkdir(exist_ok=True)
    (pasta / "planilha.json").write_text(json.dumps({"abas": abas}), encoding="utf-8")
    return pasta


@pytest.mark.parametrize("formula,dica", [
    ("=SOMA(C2:C31)", "SUM"), ("=SE(A2>0;1;0)", "IF"), ("=PROCV(A2,B:C,2,0)", "VLOOKUP"),
    ("=MÉDIA(C2:C9)", "AVERAGE"), ("=media(C2:C9)", "AVERAGE"), ("=CONT.SE(A:A,1)", "COUNTIF"),
    ("=SOMASE(A:A,1,B:B)", "SUMIF"), ("=SUM(C2;C3)", "vírgula"), ("=IF(A2>0;1;0)", "vírgula"),
])
def test_formulas_em_portugues_ou_com_ponto_e_virgula_sao_recusadas(tmp_path, formula, dica):
    pasta = _escreve(tmp_path / "p", [{"nome": "A", "colunas": ["x"], "linhas": [[formula]]}])
    with pytest.raises(ValueError) as err:
        ep.ler_planilha_json(pasta)
    assert dica in str(err.value) and "A2" in str(err.value)


def test_formulas_validas_passam(tmp_path):
    pasta = _escreve(tmp_path / "p", [{"nome": "A", "colunas": ["x"], "linhas": [
        ["=SUM(C2:C31)"], ['=IF(A2="a;b",1,0)'], ["=ISERROR(A1)"], ['=CONCATENATE("SOMA(";A1)']]}])
    # o último tem ; fora de aspas -> recusado; os três primeiros passam
    with pytest.raises(ValueError, match="vírgula"):
        ep.ler_planilha_json(pasta)
    pasta = _escreve(tmp_path / "q", [{"nome": "A", "colunas": ["x"], "linhas": [
        ["=SUM(C2:C31)"], ['=IF(A2="a;b",1,0)'], ["=ISERROR(A1)"], ['="SOMA("&A1']]}])
    assert len(ep.ler_planilha_json(pasta)) == 1


def _xml_estilos(arq):
    z = zipfile.ZipFile(arq)
    return ET.fromstring(z.read("xl/styles.xml")), ET.fromstring(z.read("xl/worksheets/sheet1.xml"))


def test_formatos_viram_numfmt_e_datas_iso_viram_serial(tmp_path):
    aba = {"nome": "F", "colunas": ["T", "N", "M", "P", "D", "D2"], "formatos": ["texto", "numero", "moeda", "percentual", "data", "data"],
           "linhas": [["001", 1234.5, 19.9, 0.25, "2026-10-01", 46296]]}
    arq = ep.gerar_xlsx([aba], tmp_path / "f.xlsx")
    est, sh = _xml_estilos(arq)
    fmts = {n.get("numFmtId"): n.get("formatCode") for n in est.iter(f"{{{NS['m']}}}numFmt")}
    assert sorted(fmts.values()) == ['"R$" #,##0.00', "dd/mm/yyyy"]
    xfs = list(est.find("m:cellXfs", NS))
    cel = {c.get("r"): c for c in sh.iter(f"{{{NS['m']}}}c")}
    ids = {r: xfs[int(cel[r].get("s"))].get("numFmtId") for r in ("A2", "B2", "C2", "D2", "E2", "F2")}
    assert ids["A2"] == "49" and ids["D2"] == "9"
    assert fmts[ids["C2"]] == '"R$" #,##0.00' and fmts[ids["E2"]] == "dd/mm/yyyy" and ids["E2"] == ids["F2"]
    assert est.find("m:cellXfs", NS).get("count") == str(len(xfs))
    # 2026-10-01 = serial 46296
    assert cel["E2"].find("m:v", NS).text == "46296" and cel["F2"].find("m:v", NS).text == "46296"
    assert cel["A1"].get("s") == "1"  # cabeçalho continua em negrito


def test_formato_desconhecido_e_data_invalida(tmp_path):
    pasta = _escreve(tmp_path / "p", [{"nome": "A", "colunas": ["x"], "formatos": ["euro"], "linhas": []}])
    with pytest.raises(ValueError, match="euro"):
        ep.ler_planilha_json(pasta)
    pasta = _escreve(tmp_path / "q", [{"nome": "A", "colunas": ["x"], "formatos": "moeda", "linhas": []}])
    with pytest.raises(ValueError, match="formatos"):
        ep.ler_planilha_json(pasta)
    pasta = _escreve(tmp_path / "r", [{"nome": "A", "colunas": ["x"], "formatos": ["data"], "linhas": [["31/02/2026"]]}])
    with pytest.raises(ValueError, match="data"):
        ep.ler_planilha_json(pasta)


def test_linhas_e_larguras_invalidas_dao_mensagem_amiga(tmp_path, capsys):
    pasta = _escreve(tmp_path / "p", [{"nome": "A", "colunas": ["x"], "linhas": [5]}])
    with pytest.raises(ValueError, match="linha 1"):
        ep.ler_planilha_json(pasta)
    pasta = _escreve(tmp_path / "q", [{"nome": "A", "colunas": ["x"], "linhas": [], "larguras": 20}])
    with pytest.raises(ValueError, match="larguras"):
        ep.ler_planilha_json(pasta)
    pasta = _escreve(tmp_path / "r", [{"nome": "A", "colunas": ["x"], "linhas": [], "larguras": ["a"]}])
    assert ep.main(["--pasta", str(pasta)]) == 1
    err = capsys.readouterr().err
    assert "larguras" in err and "Traceback" not in err


def test_erro_inesperado_vai_pro_log_e_mensagem_amiga(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MAQUINA_HOME", str(tmp_path / "home"))
    pasta = _escreve(tmp_path / "p", [{"nome": "A", "colunas": ["x"], "linhas": []}])

    def boom(*a, **k):
        raise RuntimeError("segredo-tecnico")

    monkeypatch.setattr(ep, "gerar_xlsx", boom)
    assert ep.main(["--pasta", str(pasta)]) == 1
    err = capsys.readouterr().err
    assert "segredo-tecnico" not in err and "log" in err
    assert "segredo-tecnico" in (tmp_path / "home" / "log" / "maquina.log").read_text()


def test_nome_de_aba_sem_caracteres_de_controle(tmp_path):
    arq = ep.gerar_xlsx([{"nome": "A\u0001b", "colunas": ["x"], "linhas": []}], tmp_path / "a.xlsx")
    wb = ET.fromstring(zipfile.ZipFile(arq).read("xl/workbook.xml"))
    assert [s.get("name") for s in wb.find("m:sheets", NS)] == ["Ab"]
