# tests/test_entregavel_pdf.py
import json
import re
from pathlib import Path

import pytest

import entregavel_pdf as ep


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
    assert sorted(x.name for x in carrossel.iterdir()) == ["guia-do-pao-01.png", "guia-do-pao-02.png"]
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
    p = _pasta(tmp_path, md="# Um\n\ntexto")
    car = tmp_path / "proj" / "pagina" / "imagens" / "carrossel"
    car.mkdir(parents=True)
    for nome in ("guia-do-pao-01.png", "guia-foto.png", "guia-do-pao-99.png"):
        (car / nome).write_bytes(b"x")
    outro = tmp_path / "proj" / "entregaveis" / "guia"
    outro.mkdir()
    (outro / "meta.json").write_text('{"titulo": "G"}')
    (outro / "conteudo.md").write_text("# G\n\ntexto")
    pytest.importorskip("playwright")
    _gerar_ou_pular(outro)
    ep.gerar(outro, "azul-laranja", carrossel=car)
    assert (car / "guia-do-pao-01.png").read_bytes() == b"x"
    assert (car / "guia-foto.png").read_bytes() == b"x"
    assert (car / "guia-01.png").exists()


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
    assert len(r["carrossel"]) == 2 and (car / "guia-do-pao-01.png").read_bytes() != b"png"


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


def test_amostra_1_e_o_sumario_e_a_2_o_primeiro_capitulo(tmp_path):
    p = _pasta(tmp_path)
    r = _gerar_ou_pular(p, "preto-dourado")
    assert [c["alvo"] for c in r["clips"]] == ["sumario", "capitulo"]
    assert r["clips"][0]["y"] < r["clips"][1]["y"]
    p2 = _pasta(tmp_path / "c", md="# Só\n\ntexto")
    (p2 / "meta.json").write_text('{"titulo": "X", "tipo": "guia"}')
    assert [c["alvo"] for c in _gerar_ou_pular(p2)["clips"]] == ["sumario", "capitulo"]
