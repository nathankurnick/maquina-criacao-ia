# tests/test_funil_oto.py
import json

import pytest

import funil_oto as fo


def _pasta(tmp_path, **oto):
    p = tmp_path / "proj" / "funil" / "upsell"
    p.mkdir(parents=True)
    base = {"formato": "video", "video": "https://www.youtube.com/watch?v=abcDEF12345",
            "checkout_url": "https://pay.kiwify.com.br/up123", "atraso_segundos": 0}
    base.update(oto)
    (p / "oto.json").write_text(json.dumps(base), encoding="utf-8")
    return p


@pytest.mark.parametrize("url,ok", [
    ("https://pay.kiwify.com.br/x", True), ("http://pay.x.com/a", False), ("https://pay.kiwify.com.br/SEU-LINK", False),
    ("#", False), ("", False), ("https://x", False),
])
def test_checkout_valido(url, ok):
    assert fo.checkout_valido(url) is ok


@pytest.mark.parametrize("entrada,trecho", [
    ("https://www.youtube.com/watch?v=abcDEF12345", "youtube-nocookie.com/embed/abcDEF12345"),
    ("https://youtu.be/abcDEF12345", "youtube-nocookie.com/embed/abcDEF12345"),
    ("https://www.youtube.com/shorts/abcDEF12345", "youtube-nocookie.com/embed/abcDEF12345"),
    ("https://vimeo.com/123456", "player.vimeo.com/video/123456"),
    ('<div id="vid_1"></div><script src="https://scripts.converteai.net/x.js"></script>', 'id="vid_1"'),
])
def test_embed_video(entrada, trecho):
    h = fo.embed_video(entrada)
    assert trecho in h and "autoplay=1" not in h


def test_embed_video_invalido():
    with pytest.raises(ValueError):
        fo.embed_video("https://site.com/video.mp4")


def test_ler_oto_padroes_e_validacoes(tmp_path):
    o = fo.ler_oto(_pasta(tmp_path))
    assert o["headline"] == fo.PADROES["headline"] and o["pre_headline"].startswith("⚠️")
    assert o["formato"] == "video" and o["atraso_segundos"] == 0
    for n, (ruim, trecho) in enumerate([({"checkout_url": "https://pay.x.com/SEU-LINK"}, "checkout"),
                         ({"formato": "texto", "video": ""}, "texto"),
                         ({"formato": "podcast"}, "formato"),
                         ({"atraso_segundos": -5}, "atraso"),
                         ({"recusar_url": "javascript:alert(1)"}, "recusar_url")]):
        p = _pasta(tmp_path / f"caso{n}", **ruim)
        with pytest.raises(ValueError, match=trecho):
            fo.ler_oto(p)


def test_botao_html_dispensa_checkout(tmp_path):
    o = fo.ler_oto(_pasta(tmp_path, checkout_url="", botao_html='<div id="kiwify-upsell"></div>'))
    assert o["botao_html"]


def test_html_oto_video_texto_atraso():
    oto = {**fo.PADROES, "formato": "video", "video": "https://youtu.be/abcDEF12345", "texto": "",
           "checkout_url": "https://pay.kiwify.com.br/a?x=1&y=2", "botao_html": "", "atraso_segundos": 90,
           "recusar_url": "https://site.com/obrigado", "headline": "Seu <pedido>"}
    h = fo.html_oto(oto, "preto-dourado")
    assert "Seu &lt;pedido&gt;" in h and 'class="aviso"' in h
    assert 'href="https://pay.kiwify.com.br/a?x=1&amp;y=2"' in h
    assert 'class="oferta escondida"' in h and "90000" in h
    assert 'href="https://site.com/obrigado"' in h and "--pg-cta:#d4af37" in h
    texto = fo.html_oto({**oto, "formato": "texto", "texto": "Parágrafo 1.\n\nParágrafo <2>.", "atraso_segundos": 0},
                        "azul-laranja")
    assert "<p>Parágrafo 1.</p>" in texto and "Parágrafo &lt;2&gt;." in texto
    assert 'class="oferta"' in texto and 'class="oferta escondida"' not in texto
    assert "<iframe" not in texto


def test_montar_e_sem_scroll_no_celular(tmp_path):
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright
    p = _pasta(tmp_path, formato="texto", video="", texto="Um texto bem comprido " * 80)
    index = fo.montar(p, "azul-laranja")
    assert index == p / "site" / "index.html"
    try:
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            pg = nav.new_page(viewport={"width": 390, "height": 844})
            pg.goto(index.as_uri())
            largura = pg.evaluate("document.documentElement.scrollWidth")
            nav.close()
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise
    assert largura <= 390


def test_publicar_sem_token_sai_3(ambiente, tmp_path, capsys):
    p = _pasta(tmp_path)
    assert fo.main(["--pasta", str(p), "--publicar"]) == 3
    out = capsys.readouterr().out
    assert "app.netlify.com/drop" in out and "login" in out.lower() and str(p / "site") in out


def test_publicar_ok_salva_e_avisa_mudanca(ambiente, tmp_path, monkeypatch, capsys):
    p = _pasta(tmp_path)
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")
    respostas = iter([{"site_id": "s1", "url": "https://a.netlify.app"}, {"site_id": "s2", "url": "https://b.netlify.app"}])
    monkeypatch.setattr(fo, "publicar_pasta", lambda token, pasta, site_id=None: next(respostas))
    assert fo.main(["--pasta", str(p), "--publicar"]) == 0
    assert json.loads((p / "config.json").read_text())["url"] == "https://a.netlify.app"
    capsys.readouterr()
    assert fo.main(["--pasta", str(p), "--publicar"]) == 0
    assert "mudou" in capsys.readouterr().out


def test_main_erros(tmp_path, capsys):
    assert fo.main(["--pasta", str(tmp_path / "nada")]) == 1
    assert "oto.json" in capsys.readouterr().err
    assert fo.main([]) == 1


@pytest.mark.parametrize("entrada,trecho", [
    ("https://vimeo.com/123456/abcdef1234", "player.vimeo.com/video/123456?h=abcdef1234"),
    ("https://vimeo.com/123456?h=abcdef1234", "player.vimeo.com/video/123456?h=abcdef1234"),
    ("https://player.vimeo.com/video/123456?h=abcdef1234", "player.vimeo.com/video/123456?h=abcdef1234"),
    ("https://player.vimeo.com/video/123456", "player.vimeo.com/video/123456"),
    ("https://www.youtube.com/embed/abcDEF12345", "youtube-nocookie.com/embed/abcDEF12345"),
    ("https://www.youtube.com/live/abcDEF12345", "youtube-nocookie.com/embed/abcDEF12345"),
    ("https://m.youtube.com/watch?v=abcDEF12345", "youtube-nocookie.com/embed/abcDEF12345"),
    ("https://www.youtube.com/watch?list=x&v=abcDEF12345", "youtube-nocookie.com/embed/abcDEF12345"),
])
def test_embed_video_variantes(entrada, trecho):
    assert trecho in fo.embed_video(entrada)


@pytest.mark.parametrize("ruim", [
    "https://evil.com/?u=youtube.com/watch?v=abcDEF12345",
    "https://evilyoutube.com/watch?v=abcDEF12345",
    "https://youtube.com.evil.com/watch?v=abcDEF12345",
    "https://evil.com/vimeo.com/123456",
])
def test_embed_video_host_ancorado(ruim):
    with pytest.raises(ValueError):
        fo.embed_video(ruim)


def _nav(pw, **kw):
    try:
        return pw.chromium.launch()
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise


def test_botao_atraso_com_e_sem_js(tmp_path):
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright
    p = _pasta(tmp_path, formato="texto", video="", texto="Oi.", atraso_segundos=1)
    uri = fo.montar(p, "azul-laranja").as_uri()
    with sync_playwright() as pw:
        nav = _nav(pw)
        pg = nav.new_page()
        pg.goto(uri)
        assert not pg.locator("#oferta").is_visible()
        pg.wait_for_timeout(1600)
        assert pg.locator("#oferta").is_visible()
        sem_js = nav.new_context(java_script_enabled=False).new_page()
        sem_js.goto(uri)
        assert sem_js.locator("#oferta .botao").is_visible()
        nav.close()


def test_semtoken_mensagens_consistentes_com_o_02(ambiente, tmp_path, capsys):
    p = _pasta(tmp_path)
    fo.main(["--pasta", str(p), "--publicar"])
    assert "maquina chaves" in capsys.readouterr().out
    (p / "config.json").write_text(json.dumps({"url": "https://a.netlify.app"}))
    fo.main(["--pasta", str(p), "--publicar"])
    out = capsys.readouterr().out
    assert "cria um endereço NOVO" in out and "maquina chaves" in out


def test_texto_usa_cor_escura_explicita():
    css = (fo.CSS).read_text(encoding="utf-8")
    assert "color:var(--pg-texto-escuro)" in [l for l in css.splitlines() if l.startswith(".texto{")][0].replace(" ", "")
