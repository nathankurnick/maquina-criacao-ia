import json

import pytest

import anuncio_criativo as ac


def _anuncio(**kw):
    a = {"id": "dor", "formato": "estatico", "headline_imagem": "Comida pronta pra **15 dias**",
         "visual": {"prompt": "marmitas", "produto": "ebook", "layout": "base"}}
    a.update(kw)
    return a


def _projeto(tmp_path, anuncios=None, com_mockup=True):
    p = tmp_path / "proj"
    (p / "anuncios").mkdir(parents=True)
    (p / "anuncios" / "anuncios.json").write_text(json.dumps({"anuncios": anuncios or [
        {"id": "dor", "angulo": "a", "formato": "estatico", "headline_imagem": "Comida pronta pra **15 dias**",
         "texto_principal": "t", "titulo": "t", "visual": {"prompt": "marmitas", "produto": "ebook", "layout": "base"}},
        {"id": "vid", "angulo": "b", "formato": "video", "hooks": ["h"], "corpo": "c", "cta_falado": "x",
         "texto_principal": "t", "titulo": "t"}]}), encoding="utf-8")
    if com_mockup:
        (p / "entregaveis" / "ebook").mkdir(parents=True)
        (p / "entregaveis" / "ebook" / "mockup.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    return p


def test_html_criativo_escapa_destaca_e_usa_layout():
    h = ac.html_criativo(_anuncio(headline_imagem="<b>Oi</b> **já**"), "9x16", "preto-dourado",
                         arte="arte.png", produto="mockup.png")
    assert "&lt;b&gt;Oi&lt;/b&gt;" in h and '<span class="destaque">já</span>' in h
    assert "quadro base f9x16" in h and 'src="arte.png"' in h and 'src="mockup.png"' in h
    assert "width:1080px;height:1920px" in h and "--pg-destaque:#d4af37" in h
    centro = ac.html_criativo(_anuncio(visual={"layout": "centro", "produto": "", "prompt": ""}), "1x1", "azul-laranja",
                              produto="mockup.png")
    assert 'class="produto"' not in centro


def test_tamanho_da_headline():
    assert 'class="headline h-curta"' in ac.html_criativo(_anuncio(headline_imagem="Curta"), "1x1", "azul-laranja")
    assert 'class="headline h-longa"' in ac.html_criativo(_anuncio(headline_imagem="x" * 80), "1x1", "azul-laranja")


def test_main_gerar_arte_exige_id(tmp_path, capsys):
    p = _projeto(tmp_path)
    assert ac.main(["--projeto", str(p), "--gerar-arte"]) == 1
    assert "--id" in capsys.readouterr().err


def test_main_sem_chave_imprime_prompts(ambiente, tmp_path, monkeypatch, capsys):
    p = _projeto(tmp_path)
    monkeypatch.setattr(ac, "compor", lambda pasta, a, paleta: [])
    assert ac.main(["--projeto", str(p), "--id", "dor", "--gerar-arte"]) == 0
    out = capsys.readouterr().out
    assert "marmitas" in out and "arte-dor-1x1.png" in out and "arte-dor-9x16.png" in out


def test_main_kie_falha_segue(ambiente, tmp_path, monkeypatch, capsys):
    p = _projeto(tmp_path)
    monkeypatch.setenv("KIE_API_KEY", "k")

    def quebra(*a, **k):
        raise ac.KieErro("Seus créditos da KIE acabaram.")

    monkeypatch.setattr(ac, "gerar_imagem", quebra)
    feitos = []
    monkeypatch.setattr(ac, "compor", lambda pasta, a, paleta: feitos.append(a["id"]) or [])
    assert ac.main(["--projeto", str(p), "--id", "dor", "--gerar-arte"]) == 0
    assert feitos == ["dor"] and "créditos" in capsys.readouterr().out


def test_main_id_inexistente_ou_video(tmp_path, capsys):
    p = _projeto(tmp_path)
    assert ac.main(["--projeto", str(p), "--id", "nao"]) == 1
    assert ac.main(["--projeto", str(p), "--id", "vid"]) == 1
    assert "estático" in capsys.readouterr().err


def test_compor_de_verdade(tmp_path):
    pytest.importorskip("playwright")
    p = _projeto(tmp_path, com_mockup=False)
    try:
        arquivos = ac.compor(p, _anuncio(visual={"prompt": "", "produto": "", "layout": "topo"}), "verde-branco")
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise
    nomes = sorted(a.name for a in arquivos)
    assert nomes == ["dor-1x1.jpg", "dor-9x16.jpg"]
    dados = (p / "anuncios" / "criativos" / "dor-9x16.jpg").read_bytes()
    assert dados[:3] == b"\xff\xd8\xff"
    assert not [x for x in (p / "anuncios" / "criativos").iterdir() if x.name.startswith(".")]


def test_9x16_tem_zonas_seguras():
    h = ac.html_criativo(_anuncio(), "9x16", "azul-laranja")
    assert "quadro base f9x16" in h and ".f9x16{padding:270px 72px 380px}" in h


def test_gerar_artes_nao_sobrescreve_existente(ambiente, tmp_path, monkeypatch, capsys):
    p = _projeto(tmp_path)
    artes = p / "anuncios" / "artes"
    artes.mkdir()
    (artes / "arte-dor-1x1.png").write_bytes(b"velha")
    monkeypatch.setenv("KIE_API_KEY", "k")
    chamadas = []

    def falsa(chave, prompt, proporcao, destino):
        chamadas.append(proporcao)

    monkeypatch.setattr(ac, "gerar_imagem", falsa)
    monkeypatch.setattr(ac, "compor", lambda pasta, a, paleta: [])
    assert ac.main(["--projeto", str(p), "--id", "dor", "--gerar-arte"]) == 0
    assert chamadas == ["9:16"]
    assert (artes / "arte-dor-1x1.png").read_bytes() == b"velha"
    assert "Reaproveitei a arte arte-dor-1x1.png (apague o arquivo pra gerar outra)." in capsys.readouterr().out


def test_id_com_slug(ambiente, tmp_path, monkeypatch):
    p = _projeto(tmp_path)
    feitos = []
    monkeypatch.setattr(ac, "compor", lambda pasta, a, paleta: feitos.append(a["id"]) or [])
    assert ac.main(["--projeto", str(p), "--id", "Dor"]) == 0
    assert feitos == ["dor"]


def test_paleta_invalida(ambiente, tmp_path, capsys):
    p = _projeto(tmp_path)
    assert ac.main(["--projeto", str(p), "--paleta", "rosa-choque"]) == 1
    err = capsys.readouterr().err
    assert "rosa-choque" in err and "azul-laranja" in err


def test_sem_mockup_layout_centro_nao_avisa(ambiente, tmp_path, monkeypatch, capsys):
    a = {"id": "dor", "angulo": "a", "formato": "estatico", "headline_imagem": "H", "texto_principal": "t",
         "titulo": "t", "visual": {"prompt": "", "produto": "ebook", "layout": "centro"}}
    p = _projeto(tmp_path, anuncios=[a], com_mockup=False)
    monkeypatch.setattr(ac, "compor", lambda pasta, a, paleta: [])
    assert ac.main(["--projeto", str(p)]) == 0
    assert "mockup" not in capsys.readouterr().out


def test_zero_estaticos(ambiente, tmp_path, monkeypatch, capsys):
    v = {"id": "vid", "angulo": "b", "formato": "video", "hooks": ["h"], "corpo": "c", "cta_falado": "x",
         "texto_principal": "t", "titulo": "t"}
    p = _projeto(tmp_path, anuncios=[v])
    assert ac.main(["--projeto", str(p)]) == 0
    assert "Nenhum anúncio estático no anuncios.json." in capsys.readouterr().out


def test_sem_chave_avisa_fundo_da_paleta(ambiente, tmp_path, monkeypatch, capsys):
    p = _projeto(tmp_path)
    monkeypatch.setattr(ac, "compor", lambda pasta, a, paleta: [])
    ac.main(["--projeto", str(p), "--id", "dor", "--gerar-arte"])
    assert "(as imagens já saíram com o fundo da paleta)" in capsys.readouterr().out
