# tests/test_pagina_render.py
import json
from pathlib import Path

import pytest

import pagina_conteudo as pc
import pagina_render as pr


def _conteudo(**troca):
    bruto = {
        "hero": {"badge": "Novo", "headline": "Aprenda **pão caseiro**", "subheadline": "Sub <b>x</b>", "cta": "QUERO"},
        "paraQuem": {"titulo": "Pra quem", "itens": [{"titulo": "Iniciante", "descricao": "d"}]},
        "conteudo": {"titulo": "O que tem", "itens": [{"icone": "livro", "titulo": "Receitas", "descricao": "d"}]},
        "incluso": {"titulo": "Incluso", "itens": [{"titulo": "Ebook", "descricao": "d"}], "nota": "Nota honesta"},
        "entrega": {"titulo": "Entrega", "itens": [{"titulo": "Acesso Imediato", "descricao": "d"}]},
        "bonus": {"titulo": "Bônus", "itens": [{"titulo": "Checklist", "descricao": "d", "valor": "R$47"}]},
        "planos": {"titulo": "Planos", "basico": {"itens": ["Tudo"], "precoDe": "R$ 97", "precoPor": "R$ 27",
                                                  "checkoutUrl": "https://pay.kiwify.com.br/a?x=1&y=2"}},
        "garantia": {"dias": 7, "texto": "Devolvemos seu dinheiro."},
        "faq": {"itens": [{"pergunta": "Funciona?", "resposta": "Sim."}]},
        "rodape": {"nomeProduto": "Pão Fácil"},
    }
    bruto.update(troca)
    return pc.normalizar(bruto)[0]


def _html(conteudo=None, config=None, imagens=None):
    return pr.render_html(conteudo or _conteudo(), config or dict(pc.CONFIG_PADRAO),
                          imagens or {"logo": "", "carrossel": [], "depoimentos": []}, ano=2026)


def test_com_destaque_escapa_e_colore():
    assert pr.com_destaque("Aprenda **<pão>** já") == 'Aprenda <span class="destaque">&lt;pão&gt;</span> já'


def test_documento_basico():
    h = _html()
    assert h.startswith("<!doctype html>") and '<html lang="pt-BR">' in h
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in h
    assert "<title>Aprenda pão caseiro</title>" in h
    assert "--pg-fundo:#0a1628" in h and ".cta{" in h
    assert "Sub &lt;b&gt;x&lt;/b&gt;" in h
    assert "© 2026 Pão Fácil" in h and pc.DISCLAIMER_PADRAO in h


def test_ctas_apontam_para_planos_e_checkout_escapado():
    h = _html()
    assert 'href="#planos"' in h and 'id="planos"' in h
    assert 'href="https://pay.kiwify.com.br/a?x=1&amp;y=2"' in h


def test_sem_planos_cta_vai_pro_checkout_ou_ancora_vazia():
    c = _conteudo()
    c["planos"]["ativo"] = False
    assert 'href="https://pay.kiwify.com.br/a?x=1&amp;y=2"' in _html(conteudo=c)
    c2 = _conteudo(planos={})
    h2 = _html(conteudo=c2)
    assert 'id="planos"' not in h2 and 'class="cta" href="#"' in h2


def test_blocos_escondidos_nao_aparecem():
    c = _conteudo(faq={"ativo": False, "itens": [{"pergunta": "P", "resposta": "R"}]})
    h = _html(conteudo=c)
    assert "Funciona?" not in h and 'class="faq"' not in h
    assert "Veja o material por dentro" not in h  # carrossel sem imagens
    assert "Veja o que estão dizendo" not in h    # depoimentos sem imagens


def test_imagens_logo_carrossel_depoimentos():
    h = _html(imagens={"logo": "img/logo.png", "carrossel": ["img/carrossel-01.png"],
                       "depoimentos": ["img/depoimento-01.jpg", "img/depoimento-02.jpg"]})
    assert '<img class="logo" src="img/logo.png" alt="Pão Fácil">' in h
    assert 'src="img/carrossel-01.png"' in h and "Veja o material por dentro" in h
    assert h.count('alt="Depoimento') == 2


def test_icone_svg_e_bonus_gratis_e_selo_premium():
    c = _conteudo()
    c["planos"]["premium"] = dict(c["planos"]["basico"], ativo=True, nome="PREMIUM", destaque=True,
                                  checkoutUrl="https://pay.kiwify.com.br/b")
    h = _html(conteudo=c)
    assert "<svg" in h and pc.ICONES["livro"][0] in h
    assert "Bônus #1" in h and "GRÁTIS" in h and "<s>R$47</s>" in h
    assert "MAIS VENDIDO" in h and "em-destaque" in h
    assert "7 DIAS PARA TESTAR" in h


def test_pixels_seo_e_head_html():
    cfg = dict(pc.CONFIG_PADRAO, paleta="preto-dourado", pixel_meta="123456789012", pixel_google="G-ABC1",
               seo_titulo="Título SEO", seo_descricao="Desc SEO", head_html='<script src="https://u.js"></script>')
    h = _html(config=cfg)
    assert "fbq('init','123456789012')" in h
    assert "googletagmanager.com/gtag/js?id=G-ABC1" in h
    assert "<title>Título SEO</title>" in h and 'content="Desc SEO"' in h
    assert '<script src="https://u.js"></script>' in h
    assert "--pg-destaque:#d4af37" in h


def _projeto(tmp_path, conteudo=None):
    pagina = tmp_path / "proj" / "pagina"
    pagina.mkdir(parents=True)
    (pagina / "conteudo.json").write_text(json.dumps(conteudo if conteudo is not None else {
        "hero": {"headline": "Oi"}, "planos": {"basico": {"checkoutUrl": "https://c.com", "precoPor": "R$ 9"}},
        "rodape": {"nomeProduto": "X"}}), encoding="utf-8")
    return tmp_path / "proj"


def test_montar_site_copia_imagens_e_recria_site(tmp_path):
    p = _projeto(tmp_path)
    img = p / "pagina" / "imagens"
    (img / "carrossel").mkdir(parents=True)
    (img / "depoimentos").mkdir()
    (img / "carrossel" / "b.png").write_bytes(b"png")
    (img / "carrossel" / "a.jpg").write_bytes(b"jpg")
    (img / "carrossel" / "nota.txt").write_text("x")
    (img / "logo.webp").write_bytes(b"w")
    velho = p / "pagina" / "site" / "lixo.html"
    velho.parent.mkdir(parents=True)
    velho.write_text("x")
    index, avisos = pr.montar_site(p)
    site = p / "pagina" / "site"
    assert index == site / "index.html" and index.exists()
    assert not velho.exists()
    assert sorted(x.name for x in (site / "img").iterdir()) == ["carrossel-01.jpg", "carrossel-02.png", "logo.webp"]
    h = index.read_text(encoding="utf-8")
    assert 'src="img/carrossel-01.jpg"' in h and 'src="img/logo.webp"' in h
    assert any("depoimento" in a for a in avisos)


def test_main_sem_conteudo_mensagem_amigavel(tmp_path, capsys):
    (tmp_path / "proj" / "pagina").mkdir(parents=True)
    assert pr.main(["--projeto", str(tmp_path / "proj")]) == 1
    err = capsys.readouterr().err
    assert "conteudo.json" in err and "Traceback" not in err


def test_main_json_quebrado(tmp_path, capsys):
    p = _projeto(tmp_path)
    (p / "pagina" / "conteudo.json").write_text("{quebrado")
    assert pr.main(["--projeto", str(p)]) == 1
    assert "conteudo.json" in capsys.readouterr().err


def test_main_ok_imprime_caminho_e_avisos(tmp_path, capsys):
    p = _projeto(tmp_path)
    assert pr.main(["--projeto", str(p)]) == 0
    out = capsys.readouterr().out
    assert "index.html" in out and "⚠️" in out


def test_main_argumento_faltando_em_portugues(capsys):
    assert pr.main([]) == 1
    assert "--projeto" in capsys.readouterr().err


def test_pagina_sem_rolagem_horizontal_no_celular(tmp_path):
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright
    p = _projeto(tmp_path, conteudo=json.loads(json.dumps({
        "hero": {"headline": "Uma headline **bem comprida** pra testar quebra de linha no celular", "cta": "QUERO"},
        "paraQuem": {"titulo": "T", "itens": [{"titulo": "A", "descricao": "d"}] * 3},
        "conteudo": {"titulo": "T", "itens": [{"icone": "livro", "titulo": "C", "descricao": "d"}] * 5},
        "bonus": {"titulo": "T", "itens": [{"titulo": "B", "descricao": "d", "valor": "R$ 47"}] * 5},
        "planos": {"basico": {"checkoutUrl": "https://c.com/umlinkmuitocompridosemespacoaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                              "precoPor": "R$ 27", "itens": ["x"]}},
        "garantia": {"texto": "t"}, "faq": {"itens": [{"pergunta": "p", "resposta": "r"}]},
        "rodape": {"nomeProduto": "X"}})))
    index, _ = pr.montar_site(p)
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


def test_href_perigoso_nunca_vai_pro_html():
    for ruim in ("javascript:alert(1)", "data:text/html,x", "texto solto", "//evil.com"):
        bruto = {"hero": {"headline": "H"}, "planos": {"basico": {"checkoutUrl": ruim, "precoPor": "R$ 1"}}}
        c, avisos = pc.normalizar(bruto)
        assert any("não é um endereço válido" in a for a in avisos)
        h = _html(conteudo=c)
        assert ruim not in h and 'class="cta" href="#"' in h
    assert pr._cta("javascript:alert(1)", "X") == '<a class="cta" href="#">X</a>'


def test_logo_so_stem_exato(tmp_path):
    p = _projeto(tmp_path)
    img = p / "pagina" / "imagens"
    img.mkdir()
    (img / "logo.backup.png").write_bytes(b"x")
    (img / "LOGO.PNG").write_bytes(b"y")
    pr.montar_site(p)
    assert sorted(x.name for x in (p / "pagina" / "site" / "img").iterdir()) == ["logo.png"]
    (img / "LOGO.PNG").unlink()
    pr.montar_site(p)
    assert not (p / "pagina" / "site" / "img" / "logo.png").exists()


def test_falha_mantem_site_antigo(tmp_path, monkeypatch, capsys):
    p = _projeto(tmp_path)
    c = p / "pagina" / "imagens" / "carrossel"
    c.mkdir(parents=True)
    for n in "ab":
        (c / f"{n}.png").write_bytes(b"x")
    pr.montar_site(p)
    site = p / "pagina" / "site"
    antigo = (site / "index.html").read_text(encoding="utf-8")
    chamadas = []

    def falha(*a, **k):
        chamadas.append(1)
        if len(chamadas) == 2:
            raise OSError("disco cheio")

    monkeypatch.setattr(pr.shutil, "copyfile", falha)
    monkeypatch.setenv("MAQUINA_HOME", str(tmp_path / "home"))
    assert pr.main(["--projeto", str(p)]) == 1
    assert (site / "index.html").read_text(encoding="utf-8") == antigo
    assert not (p / "pagina" / ".site-novo").exists()


def test_com_destaque_sem_asteriscos_sobrando():
    assert "*" not in pr.com_destaque("a ** b **c** d ** e")
    assert pr.com_destaque("x ** ** y") == "x   y"
    assert pr.com_destaque("**a** e **b") == '<span class="destaque">a</span> e b'


def test_logo_alt_noscript_e_foco():
    cfg = dict(pc.CONFIG_PADRAO, pixel_meta="123456789012")
    h = _html(config=cfg, imagens={"logo": "img/logo.png", "carrossel": [], "depoimentos": []})
    assert '<img class="logo" src="img/logo.png" alt="Pão Fácil">' in h
    assert '<noscript><img height="1" width="1" style="display:none" ' in h
    assert "id=123456789012&amp;ev=PageView&amp;noscript=1" in h
    assert "a.cta:focus-visible,summary:focus-visible{outline" in h


def test_aspas_escapadas_em_atributos_e_texto():
    c = _conteudo(hero={"headline": 'Diga "oi"', "cta": 'Vai "já"'})
    c["planos"]["basico"]["checkoutUrl"] = 'https://x.com/a"onclick="y'
    h = _html(conteudo=c)
    assert 'href="https://x.com/a&quot;onclick=&quot;y"' in h
    assert "Diga &quot;oi&quot;" in h and "Vai &quot;já&quot;" in h
