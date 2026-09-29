# tests/test_entregavel_pdf.py
import json
import re
from pathlib import Path

import pytest

import entregavel_pdf as ep


def _capa_falsa(p, w=1240, h=1754):
    import struct
    import zlib

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))

    linha = b"\x00" + bytes([200, 60, 30]) * w
    (p / "capa.png").write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                                 + chunk(b"IDAT", zlib.compress(linha * h)) + chunk(b"IEND", b""))


def _tamanho_jpeg(d):
    i = 2
    while i < len(d):
        marc = d[i + 1]
        n = int.from_bytes(d[i + 2:i + 4], "big")
        if marc in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(d[i + 7:i + 9], "big"), int.from_bytes(d[i + 5:i + 7], "big")
        i += 2 + n
    raise AssertionError("sem SOF")


def _pasta(tmp_path, tipo="ebook", md=None, meta=None):
    p = tmp_path / "proj" / "entregaveis" / "guia-do-pao"
    p.mkdir(parents=True)
    (p / "meta.json").write_text(json.dumps(meta or {"titulo": "Guia do Pão", "subtitulo": "Do zero",
                                                    "tipo": tipo, "autor": "Ana"}), encoding="utf-8")
    (p / "conteudo.md").write_text(md or "# Capítulo 1\n\nTexto **forte**.\n\n## Parte\n\n- [ ] item\n\n"
                                          "# Capítulo 2\n\n> **Dica:** use farinha boa\n", encoding="utf-8")
    return p


def test_ler_meta_valida(tmp_path):
    p = _pasta(tmp_path)
    assert ep.ler_meta(p)["tipo"] == "ebook"
    (p / "meta.json").write_text('{"tipo": "ebook"}')
    with pytest.raises(ValueError, match="titulo"):
        ep.ler_meta(p)
    (p / "meta.json").write_text('{"titulo": "X", "tipo": "novela"}')
    with pytest.raises(ValueError, match="tipo"):
        ep.ler_meta(p)
    (p / "meta.json").write_text("{quebrado")
    with pytest.raises(ValueError, match="meta.json"):
        ep.ler_meta(p)


def test_montar_html_documento_tem_capa_sumario_e_paleta():
    html = ep.montar_html({"titulo": "Guia <do> Pão", "subtitulo": "S", "tipo": "ebook", "autor": "Ana"},
                          "# Um\n\n## Dois\n\ntexto", "preto-dourado")
    assert "Guia &lt;do&gt; Pão" in html and "--pg-destaque:#d4af37" in html
    assert 'class="capa"' in html and 'class="sumario"' in html
    assert '<a href="#um">Um</a>' in html and 'class="n2"' in html
    assert "@page{size:A4" in html


def test_montar_html_com_imagem_de_capa():
    html = ep.montar_html({"titulo": "T", "tipo": "guia"}, "# A", "azul-laranja", capa_img="capa.png")
    assert '<img class="capa-imagem" src="capa.png" alt="">' in html


def test_montar_html_slides():
    html = ep.montar_html({"titulo": "Aula 1", "subtitulo": "Intro", "tipo": "slides"},
                          "## Objetivo\n\n- aprender\n---\n## Passo 2\n\ntexto", "verde-branco")
    assert html.count('class="slide') == 3  # título + 2
    assert "@page{size:1280px 720px" in html and 'class="sumario"' not in html


def test_gerar_pdf_de_verdade_com_amostras_e_carrossel(tmp_path):
    pytest.importorskip("playwright")
    md = "\n\n".join(f"# Capítulo {i}\n\n" + ("Um parágrafo de texto do capítulo. " * 60) for i in range(1, 5))
    p = _pasta(tmp_path, md=md)
    carrossel = tmp_path / "proj" / "pagina" / "imagens" / "carrossel"
    try:
        r = ep.gerar(p, "azul-laranja", carrossel=carrossel)
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise
    pdf = p / "guia-do-pao.pdf"
    assert r["pdf"] == pdf and pdf.read_bytes()[:4] == b"%PDF"
    assert len(re.findall(rb"/Type\s*/Page(?!s)", pdf.read_bytes())) >= 6
    assert [a.name for a in r["amostras"]] == ["amostra-1.png", "amostra-2.png"]
    assert sorted(x.name for x in carrossel.iterdir()) == ["50-guia-do-pao-01.png", "50-guia-do-pao-02.png"]
    assert not (p / ".render.html").exists()


def test_gerar_slides_de_verdade(tmp_path):
    pytest.importorskip("playwright")
    p = _pasta(tmp_path, tipo="slides", md="## A\n\n- x\n---\n## B\n\n- y")
    try:
        r = ep.gerar(p, "grafite-ciano")
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise
    dados = r["pdf"].read_bytes()
    assert len(re.findall(rb"/Type\s*/Page(?!s)", dados)) == 3


def test_main_erros_amigaveis(tmp_path, capsys):
    assert ep.main(["--pasta", str(tmp_path / "nao-existe")]) == 1
    assert "meta.json" in capsys.readouterr().err
    p = _pasta(tmp_path)
    (p / "conteudo.md").unlink()
    assert ep.main(["--pasta", str(p)]) == 1
    assert "conteudo.md" in capsys.readouterr().err
    assert ep.main([]) == 1
    assert "--pasta" in capsys.readouterr().err


def test_main_ctrl_c(tmp_path, monkeypatch, capsys):
    p = _pasta(tmp_path)

    def cancela(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(ep, "gerar", cancela)
    assert ep.main(["--pasta", str(p)]) == 130
    assert "Cancelado" in capsys.readouterr().err


def _tamanho_png(arq):
    d = arq.read_bytes()
    return int.from_bytes(d[16:20], "big"), int.from_bytes(d[20:24], "big")


def test_montar_html_envolve_cada_capitulo():
    html = ep.montar_html({"titulo": "T", "subtitulo": "", "autor": "", "tipo": "ebook"}, "# A\n\ntexto\n\n## sub\n\n# B\n\nfim", "azul-laranja")
    assert html.count('<section class="capitulo">') == 2 and html.count("</section>") >= 4
    assert html.index('<section class="capitulo"><h1') < html.index('id="sub"') < html.rindex('<section class="capitulo">')


def _gerar_ou_pular(p, tipo_paleta="azul-laranja"):
    pytest.importorskip("playwright")
    try:
        return ep.gerar(p, tipo_paleta)
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise


def test_amostras_sao_paginas_a4_e_a_primeira_e_o_sumario(tmp_path):
    p = _pasta(tmp_path)  # 2 capítulos curtos
    r = _gerar_ou_pular(p)
    assert [_tamanho_png(a) for a in r["amostras"]] == [(794, 1123), (794, 1123)]
    assert r["amostras"][0].read_bytes() != r["amostras"][1].read_bytes()


def test_ebook_de_um_capitulo_da_sumario_e_capitulo(tmp_path):
    p = _pasta(tmp_path, md="# Único\n\nPouco texto.")
    r = _gerar_ou_pular(p)
    assert len(r["amostras"]) == 2
    assert [_tamanho_png(a) for a in r["amostras"]] == [(794, 1123), (794, 1123)]


def test_slides_amostras_sao_os_slides_2_e_3(tmp_path):
    p = _pasta(tmp_path, tipo="slides", md="## A\n\n- x\n---\n## B\n\n- y")
    r = _gerar_ou_pular(p, "grafite-ciano")
    assert [_tamanho_png(a) for a in r["amostras"]] == [(1280, 720), (1280, 720)]


def test_carrossel_so_apaga_os_proprios_arquivos(tmp_path):
    pytest.importorskip("playwright")
    p = _pasta(tmp_path, md="# Um\n\ntexto")  # slug guia-do-pao
    car = tmp_path / "proj" / "pagina" / "imagens" / "carrossel"
    car.mkdir(parents=True)
    velhos = ("50-guia-do-pao-01.png", "50-guia-do-pao-99.png", "07-guia-do-pao-02.jpg")  # meus (qualquer NN)
    alheios = ("50-guia-foto.png", "guia-do-pao-x.png", "50-guia-do-pao-x.png", "aluno.png", "50-guia-do-pao-01.webp")
    for nome in velhos + alheios:
        (car / nome).write_bytes(b"x")
    outro = tmp_path / "proj" / "entregaveis" / "guia"
    outro.mkdir()
    (outro / "meta.json").write_text('{"titulo": "G"}')
    (outro / "conteudo.md").write_text("# G\n\ntexto")
    _gerar_ou_pular(outro)
    ep.gerar(outro, "azul-laranja", carrossel=car)
    assert (car / "50-guia-01.png").exists()
    ep.gerar(p, "azul-laranja", carrossel=car, ordem=7)
    for nome in alheios + ("50-guia-01.png",):
        assert (car / nome).exists(), nome
    for nome in velhos:
        assert not (car / nome).exists(), nome
    assert (car / "07-guia-do-pao-01.png").exists()


def test_ordem_define_o_prefixo_e_a_ordenacao(tmp_path):
    pytest.importorskip("playwright")
    car = tmp_path / "car"
    a = _pasta(tmp_path / "a", md="# Um\n\ntexto")
    b = tmp_path / "b" / "bonus"
    b.mkdir(parents=True)
    (b / "meta.json").write_text('{"titulo": "B"}')
    (b / "conteudo.md").write_text("# B\n\ntexto")
    _gerar_ou_pular(a)
    ep.gerar(b, "azul-laranja", carrossel=car, ordem=2)
    ep.gerar(a, "azul-laranja", carrossel=car, ordem=1)
    nomes = sorted(x.name for x in car.iterdir())
    assert nomes[0].startswith("01-guia-do-pao-") and nomes[-1].startswith("02-bonus-")
    assert ep.main(["--pasta", str(a), "--ordem", "0"]) == 1
    assert ep.main(["--pasta", str(a), "--ordem", "100"]) == 1
    assert ep.main(["--pasta", str(a), "--ordem", "x"]) == 1


def test_capa_no_carrossel_e_jpeg_de_800px(tmp_path):
    pytest.importorskip("playwright")
    p = _pasta(tmp_path, md="# Um\n\ntexto")
    _capa_falsa(p)
    car = tmp_path / "car"
    r = ep.gerar(p, "azul-laranja", carrossel=car)
    nomes = sorted(x.name for x in car.iterdir())
    assert nomes == ["50-guia-do-pao-01.jpg", "50-guia-do-pao-02.png", "50-guia-do-pao-03.png"]
    d = (car / "50-guia-do-pao-01.jpg").read_bytes()
    assert d[:3] == b"\xff\xd8\xff"
    assert _tamanho_jpeg(d)[0] == 800 and len(r["carrossel"]) == 3


def test_pdf_antigo_sobrevive_se_a_geracao_falha(tmp_path, monkeypatch):
    p = _pasta(tmp_path)
    (p / "guia-do-pao.pdf").write_bytes(b"%PDF-antigo")

    def falha(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(ep, "_salvar_pdf", falha)
    pytest.importorskip("playwright")
    with pytest.raises(RuntimeError):
        ep.gerar(p, "azul-laranja")
    assert (p / "guia-do-pao.pdf").read_bytes() == b"%PDF-antigo"
    assert not list(p.glob(".*"))


def test_slides_nao_copiam_capa_pro_carrossel(tmp_path):
    p = _pasta(tmp_path, tipo="slides", md="## A\n\n- x\n---\n## B\n\n- y")
    (p / "capa.png").write_bytes(b"png")
    car = tmp_path / "car"
    pytest.importorskip("playwright")
    r = ep.gerar(p, "grafite-ciano", carrossel=car)
    assert len(r["carrossel"]) == 2 and (car / "50-guia-do-pao-01.png").read_bytes() != b"png"


def test_pasta_relativa_usa_nome_da_pasta(tmp_path, monkeypatch):
    p = _pasta(tmp_path)
    monkeypatch.chdir(p)
    r = _gerar_ou_pular(Path("."))
    assert r["pdf"].name == "guia-do-pao.pdf"


def test_arquivos_fora_de_utf8_dao_mensagem_amiga(tmp_path):
    p = _pasta(tmp_path)
    (p / "meta.json").write_bytes('{"titulo": "Pão"}'.encode("latin-1"))
    with pytest.raises(ValueError, match="UTF-8"):
        ep.ler_meta(p)
    p2 = _pasta(tmp_path / "b")
    (p2 / "conteudo.md").write_bytes("# Pão\n".encode("latin-1"))
    with pytest.raises(ValueError, match="UTF-8"):
        ep.gerar(p2, "azul-laranja")


def test_ebook_curto_usa_dois_capitulos_e_um_so_capitulo_cai_no_main(tmp_path):
    r = _gerar_ou_pular(_pasta(tmp_path), "preto-dourado")
    assert [c["alvo"] for c in r["clips"]] == ["capitulo", "capitulo"]
    assert r["clips"][0]["y"] < r["clips"][1]["y"]
    p2 = _pasta(tmp_path / "c", md="# Só\n\ntexto")
    (p2 / "meta.json").write_text('{"titulo": "X", "tipo": "guia"}')
    r2 = _gerar_ou_pular(p2)
    assert [c["alvo"] for c in r2["clips"]] == ["main", "main"]
    assert [_tamanho_png(a) for a in r2["amostras"]] == [(794, 1123), (794, 1123)]


def _rico(n_caixas):
    return "\n\n".join(f"> **Dica:** dica número {i}" for i in range(n_caixas))


def test_amostras_escolhem_os_capitulos_mais_visuais(tmp_path):
    md = ("# Introdução\n\n" + "Texto corrido sem nada especial. " * 30 + "\n\n"
          "# Capítulo rico\n\n" + _rico(3) + "\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n"
          "# Capítulo simples\n\ntexto\n\n# Capítulo médio\n\n" + _rico(1))
    r = _gerar_ou_pular(_pasta(tmp_path, md=md))
    assert [c["alvo"] for c in r["clips"]] == ["capitulo", "capitulo"]
    ys = [c["y"] for c in r["clips"]]
    assert ys[1] - ys[0] >= 2 * 1123  # rico (2º capítulo) primeiro, médio (4º) depois; intro e simples ficam de fora


def test_empate_de_pontuacao_segue_a_ordem_do_documento(tmp_path):
    md = "# A\n\n" + _rico(1) + "\n\n# B\n\n" + _rico(1) + "\n\n# C\n\n" + _rico(1)
    r = _gerar_ou_pular(_pasta(tmp_path, md=md))
    assert r["clips"][0]["y"] < r["clips"][1]["y"]


def test_sumario_longo_vai_primeiro(tmp_path):
    md = "\n\n".join(f"# Capítulo {i}\n\ntexto {i}" for i in range(1, 9))
    r = _gerar_ou_pular(_pasta(tmp_path, md=md))
    assert [c["alvo"] for c in r["clips"]] == ["sumario", "capitulo"]


def test_sumario_curto_nao_e_candidato(tmp_path):
    md = "# A\n\ntexto\n\n# B\n\n" + _rico(2)
    r = _gerar_ou_pular(_pasta(tmp_path, md=md))
    assert [c["alvo"] for c in r["clips"]] == ["capitulo", "capitulo"]


def test_checklist_so_com_h2_usa_recortes_do_main(tmp_path):
    md = "## Antes\n\n" + "\n".join(f"- [ ] item {i}" for i in range(80)) + "\n\n## Depois\n\n- [ ] fim"
    p = _pasta(tmp_path, tipo="checklist", md=md, meta={"titulo": "C", "tipo": "checklist"})
    r = _gerar_ou_pular(p)
    assert [c["alvo"] for c in r["clips"]] == ["main", "main"]
    assert r["clips"][1]["y"] - r["clips"][0]["y"] == 1123
    assert [_tamanho_png(a) for a in r["amostras"]] == [(794, 1123), (794, 1123)]


def test_capa_desatualizada_avisa(tmp_path, capsys):
    import os
    p = _pasta(tmp_path, md="# Um\n\ntexto")
    _capa_falsa(p, 100, 141)
    os.utime(p / "capa.png", (1000, 1000))
    os.utime(p / "meta.json", (2000, 2000))
    r = _gerar_ou_pular(p)
    assert any("mais antiga que o meta.json" in a for a in r["avisos"])
    assert ep.main(["--pasta", str(p)]) == 0
    assert "⚠️ A capa (capa.png) é mais antiga que o meta.json" in capsys.readouterr().out
    os.utime(p / "capa.png", (3000, 3000))
    assert not _gerar_ou_pular(p)["avisos"]


def test_roteiro_nao_vai_pro_carrossel(tmp_path, capsys):
    pytest.importorskip("playwright")
    p = _pasta(tmp_path, tipo="roteiro", md="# Aula 1\n\ntexto")
    car = tmp_path / "car"
    assert ep.main(["--pasta", str(p), "--carrossel", str(car)]) == 0
    assert not car.exists() or not list(car.iterdir())
    assert "roteiro" in capsys.readouterr().out.lower()


def test_amostras_antigas_so_saem_depois_de_render_ok(tmp_path, monkeypatch):
    pytest.importorskip("playwright")
    p = _pasta(tmp_path)
    (p / "previa").mkdir()
    (p / "previa" / "amostra-1.png").write_bytes(b"velha")
    (p / "previa" / "amostra-2.png").write_bytes(b"velha")

    def falha(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(ep, "_salvar_pdf", falha)
    with pytest.raises(RuntimeError):
        ep.gerar(p, "azul-laranja")
    assert (p / "previa" / "amostra-1.png").read_bytes() == b"velha"
    monkeypatch.undo()
    r = _gerar_ou_pular(p)
    assert r["amostras"][0].read_bytes() != b"velha" and sorted(x.name for x in (p / "previa").iterdir()) == [
        "amostra-1.png", "amostra-2.png"]


def test_carrossel_apaga_tambem_o_formato_antigo_sem_prefixo(tmp_path):
    pytest.importorskip("playwright")
    p = _pasta(tmp_path, md="# Um\n\ntexto")
    car = tmp_path / "car"
    car.mkdir()
    for nome in ("guia-do-pao-01.png", "guia-do-pao-02.png", "guia-do-pao-x.png", "outro-01.png"):
        (car / nome).write_bytes(b"x")
    ep.gerar(p, "azul-laranja", carrossel=car)
    nomes = sorted(x.name for x in car.iterdir())
    assert "guia-do-pao-01.png" not in nomes and "guia-do-pao-02.png" not in nomes
    assert "guia-do-pao-x.png" in nomes and "outro-01.png" in nomes


def test_ordem_invalida_em_portugues(tmp_path, capsys):
    p = _pasta(tmp_path)
    for v in ("0", "100", "x"):
        assert ep.main(["--pasta", str(p), "--ordem", v]) == 1
        err = capsys.readouterr().err
        assert "--ordem" in err and "1 a 99" in err and "invalid" not in err and "argument" not in err


def test_aviso_de_capa_antiga_nao_cita_paleta(tmp_path):
    import os
    p = _pasta(tmp_path, md="# Um\n\ntexto")
    _capa_falsa(p, 100, 141)
    os.utime(p / "capa.png", (1000, 1000))
    os.utime(p / "meta.json", (2000, 2000))
    aviso = _gerar_ou_pular(p)["avisos"][0]
    assert "paleta" not in aviso and "título, subtítulo ou autor" in aviso


def test_capa_jpeg_temporaria_some_mesmo_se_o_render_falha(tmp_path, monkeypatch):
    pytest.importorskip("playwright")
    p = _pasta(tmp_path, md="# Um\n\ntexto")
    _capa_falsa(p, 100, 141)

    def falha(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(ep.shutil, "copyfile", falha)
    with pytest.raises(RuntimeError):
        ep.gerar(p, "azul-laranja", carrossel=tmp_path / "car")
    assert not list(p.glob(".*"))
