# tests/test_anuncio_exportar.py
import csv
import json
import zipfile

import anuncio_exportar as ae

ANUNCIOS = [
    {"id": "dor", "angulo": "Cansaço", "formato": "estatico", "headline_imagem": "Comida pronta",
     "texto_principal": "Chega de cozinhar todo dia.", "titulo": "Marmitas Já", "descricao": "", "cta": "Saiba mais",
     "visual": {"prompt": "", "produto": "", "layout": "base"}},
    {"id": "vid", "angulo": "Rotina", "formato": "video", "hooks": ["Hook um", "Hook dois"], "corpo": "Corpo",
     "cta_falado": "Clica", "cenas": ["Cena 1"], "texto_principal": "Texto", "titulo": "Ti", "descricao": "",
     "cta": "Saiba mais"},
]


def test_textos_md(tmp_path):
    (tmp_path / "dor-1x1.jpg").write_bytes(b"x")
    md = ae.textos_md(ANUNCIOS, "https://x.netlify.app", tmp_path)
    assert "## dor — Cansaço" in md and "Chega de cozinhar todo dia." in md
    assert "dor-1x1.jpg" in md and "https://x.netlify.app" in md and "Saiba mais" in md
    assert "vid" not in md.split("## dor")[0]
    sem_link = ae.textos_md(ANUNCIOS, "", tmp_path)
    assert "Publique a página" in sem_link


def test_roteiros_md():
    md = ae.roteiros_md(ANUNCIOS)
    assert "Hook 1" in md and "Hook dois" in md and "Corpo" in md and "Cena 1" in md
    assert ae.roteiros_md([ANUNCIOS[0]]) == ""


def test_linhas_plano():
    linhas = ae.linhas_plano(ANUNCIOS)
    assert len(linhas) == 3
    assert linhas[0][:3] == ["dor", "Cansaço", "Estático"] and linhas[0][4] == "Aberto (Advantage+)"
    assert linhas[1][3] == "Hook 1: Hook um" and linhas[2][6] == "A testar"


def _projeto(tmp_path):
    p = tmp_path / "proj"
    (p / "anuncios").mkdir(parents=True)
    brutos = [{k: v for k, v in a.items()} for a in ANUNCIOS]
    (p / "anuncios" / "anuncios.json").write_text(json.dumps({"anuncios": brutos}), encoding="utf-8")
    return p


def test_exportar_grava_arquivos(tmp_path):
    p = _projeto(tmp_path)
    r = ae.exportar(p)
    a = p / "anuncios"
    assert (a / "textos.md").exists() and (a / "roteiros.md").exists()
    assert r["plano"].name in ("plano-de-teste.xlsx", "plano-de-teste.csv")
    if r["plano"].suffix == ".xlsx":
        assert "xl/worksheets/sheet1.xml" in zipfile.ZipFile(r["plano"]).namelist()


def test_exportar_cai_pra_csv_sem_o_03(tmp_path, monkeypatch):
    p = _projeto(tmp_path)
    monkeypatch.setattr(ae, "gerar_xlsx", None)
    r = ae.exportar(p)
    assert r["plano"].suffix == ".csv"
    linhas = list(csv.reader(r["plano"].open(encoding="utf-8-sig")))
    assert linhas[0][0] == "Anúncio" and len(linhas) == 4


def test_main(tmp_path, capsys):
    p = _projeto(tmp_path)
    assert ae.main(["--projeto", str(p)]) == 0
    assert "textos.md" in capsys.readouterr().out
    assert ae.main(["--projeto", str(tmp_path / "nada")]) == 1
    assert ae.main([]) == 1


def test_formula_nao_vira_formula():
    a = [dict(ANUNCIOS[0], id="f", angulo="=SOMA(1)"),
         dict(ANUNCIOS[1], id="v", hooks=["=1+1", "+cmd"], angulo="@x")]
    for linha in ae.linhas_plano(a):
        for c in linha:
            assert not str(c).startswith(("=", "+", "@", "-"))


def test_xlsx_sem_formula(tmp_path):
    p = _projeto(tmp_path)
    j = p / "anuncios" / "anuncios.json"
    dados = json.loads(j.read_text(encoding="utf-8"))
    dados["anuncios"][0]["angulo"] = "=HYPERLINK(1)"
    j.write_text(json.dumps(dados), encoding="utf-8")
    r = ae.exportar(p)
    if r["plano"].suffix == ".xlsx":
        assert "<f>" not in zipfile.ZipFile(r["plano"]).read("xl/worksheets/sheet1.xml").decode()


def test_erro_inesperado_vai_pro_log(tmp_path, monkeypatch, capsys, ambiente):
    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(ae, "exportar", boom)
    assert ae.main(["--projeto", str(tmp_path)]) == 1
    assert "Traceback" not in capsys.readouterr().err
    assert (ambiente / "home" / "log" / "maquina.log").exists()


def test_ctrl_c(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise KeyboardInterrupt
    monkeypatch.setattr(ae, "exportar", boom)
    assert ae.main(["--projeto", str(tmp_path)]) == 130
    assert "Cancelado." in capsys.readouterr().err


def test_sem_videos_apaga_roteiros_velho(tmp_path):
    p = _projeto(tmp_path)
    ae.exportar(p)
    assert (p / "anuncios" / "roteiros.md").exists()
    j = p / "anuncios" / "anuncios.json"
    dados = json.loads(j.read_text(encoding="utf-8"))
    dados["anuncios"] = dados["anuncios"][:1]
    j.write_text(json.dumps(dados), encoding="utf-8")
    ae.exportar(p)
    assert not (p / "anuncios" / "roteiros.md").exists()


def test_apaga_plano_do_outro_formato(tmp_path, monkeypatch):
    p = _projeto(tmp_path)
    (p / "anuncios" / "plano-de-teste.xlsx").write_bytes(b"x")
    monkeypatch.setattr(ae, "gerar_xlsx", None)
    ae.exportar(p)
    assert not (p / "anuncios" / "plano-de-teste.xlsx").exists()
    assert (p / "anuncios" / "plano-de-teste.csv").exists()


def test_orfaos_listados(tmp_path, capsys):
    p = _projeto(tmp_path)
    c = p / "anuncios" / "criativos"
    c.mkdir()
    (c / "dor-1x1.jpg").write_bytes(b"x")
    (c / "velho-1x1.jpg").write_bytes(b"x")
    (c / "velho-9x16.jpg").write_bytes(b"x")
    r = ae.exportar(p)
    assert [o.name for o in r["orfaos"]] == ["velho-1x1.jpg", "velho-9x16.jpg"]
    assert (c / "velho-1x1.jpg").exists()
    ae.main(["--projeto", str(p)])
    out = capsys.readouterr().out
    assert "⚠️" in out and "velho-1x1.jpg" in out and "dor-1x1.jpg" not in out


def test_roteiros_com_link_e_descricao():
    md = ae.roteiros_md([dict(ANUNCIOS[1], descricao="Desc do vídeo")], "https://x.app")
    assert "**Link:** https://x.app" in md and "**Descrição:** Desc do vídeo" in md
    assert "Publique a página" in ae.roteiros_md([ANUNCIOS[1]], "")


def test_textos_bloco_e_sem_rode_o_script(tmp_path):
    md = ae.textos_md(ANUNCIOS, "", tmp_path)
    assert "```text\nChega de cozinhar todo dia.\n```" in md
    assert "imagens ainda não montadas" in md and "anuncio_criativo" not in md


def test_csv_ponto_e_virgula_e_guarda_de_formula(tmp_path, monkeypatch):
    p = _projeto(tmp_path)
    monkeypatch.setattr(ae, "gerar_xlsx", None)
    r = ae.exportar(p)
    linhas = list(csv.reader(r["plano"].open(encoding="utf-8-sig"), delimiter=";"))
    assert linhas[0][0] == "Anúncio" and len(linhas[0]) == 8
    assert ae._seguro("\tx").startswith(" ") and ae._seguro("\rx").startswith(" ")
