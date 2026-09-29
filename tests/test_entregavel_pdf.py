# tests/test_entregavel_pdf.py
import json
import re

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
