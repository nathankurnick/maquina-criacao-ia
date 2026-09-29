import json

import pytest

import anuncio_dados as ad


def _estatico(**kw):
    base = {"id": "Dor Cozinha", "angulo": "Cansaço", "formato": "estatico",
            "headline_imagem": "Comida pronta", "texto_principal": "Texto", "titulo": "Título"}
    base.update(kw)
    return base


def _video(**kw):
    base = {"id": "v1", "angulo": "Rotina", "formato": "video", "hooks": ["Hook A", "Hook B"],
            "corpo": "Corpo", "cta_falado": "Clica", "texto_principal": "T", "titulo": "Ti"}
    base.update(kw)
    return base


def _gravar(tmp_path, anuncios):
    (tmp_path / "anuncios.json").write_text(json.dumps({"anuncios": anuncios}), encoding="utf-8")
    return tmp_path


def test_normaliza_estatico_e_video(tmp_path):
    a, v = ad.ler_anuncios(_gravar(tmp_path, [_estatico(), _video(cenas=["c1"])]))
    assert a["id"] == "dor-cozinha" and a["cta"] == "Saiba mais" and a["descricao"] == ""
    assert a["visual"] == {"prompt": "", "produto": "", "layout": "base"}
    assert v["hooks"] == ["Hook A", "Hook B"] and v["cenas"] == ["c1"] and v["cta"] == "Saiba mais"


@pytest.mark.parametrize("ruim,trecho", [
    (_estatico(headline_imagem=""), "headline_imagem"),
    (_estatico(formato="carrossel"), "formato"),
    (_estatico(cta="Compre já"), "cta"),
    (_estatico(visual={"layout": "lado"}), "layout"),
    (_video(hooks=[]), "hooks"),
    (_video(corpo=" "), "corpo"),
    (_estatico(id="!!!"), "id"),
])
def test_erros_amigaveis(tmp_path, ruim, trecho):
    with pytest.raises(ValueError, match=trecho):
        ad.ler_anuncios(_gravar(tmp_path, [ruim]))


def test_id_repetido(tmp_path):
    with pytest.raises(ValueError, match="repetido"):
        ad.ler_anuncios(_gravar(tmp_path, [_estatico(), _estatico(id="dor-cozinha")]))


def test_arquivo_ausente_ou_quebrado(tmp_path):
    with pytest.raises(ValueError, match="anuncios.json"):
        ad.ler_anuncios(tmp_path)
    (tmp_path / "anuncios.json").write_text("{quebrado")
    with pytest.raises(ValueError, match="anuncios.json"):
        ad.ler_anuncios(tmp_path)
    (tmp_path / "anuncios.json").write_text('{"anuncios": []}')
    with pytest.raises(ValueError, match="anúncio"):
        ad.ler_anuncios(tmp_path)


def test_destino_e_paleta(tmp_path):
    assert ad.destino(tmp_path) == "" and ad.paleta_do_projeto(tmp_path) == ""
    (tmp_path / "pagina").mkdir()
    (tmp_path / "pagina" / "config.json").write_text(json.dumps({"url": "https://x.netlify.app", "paleta": "preto-dourado"}))
    assert ad.destino(tmp_path) == "https://x.netlify.app"
    assert ad.paleta_do_projeto(tmp_path) == "preto-dourado"
    (tmp_path / "pagina" / "config.json").write_text("{quebrado")
    assert ad.destino(tmp_path) == "" and ad.paleta_do_projeto(tmp_path) == ""


def test_hooks_e_cenas_string_viram_lista(tmp_path):
    (v,) = ad.ler_anuncios(_gravar(tmp_path, [_video(hooks="Um só hook", cenas="uma cena")]))
    assert v["hooks"] == ["Um só hook"] and v["cenas"] == ["uma cena"]


@pytest.mark.parametrize("campo", ["hooks", "cenas"])
def test_hooks_cenas_tipo_errado(tmp_path, campo):
    with pytest.raises(ValueError, match=f"{campo} precisa ser uma lista de textos"):
        ad.ler_anuncios(_gravar(tmp_path, [_video(**{campo: {"a": 1}})]))


def test_arquivo_ilegivel(tmp_path):
    (tmp_path / "anuncios.json").mkdir()
    with pytest.raises(ValueError, match="Não consegui ler"):
        ad.ler_anuncios(tmp_path)
