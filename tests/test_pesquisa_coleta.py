import json

import pytest

from coleta import Coletor, montar_url


def _ad(aid, **extra):
    base = {
        "ad_archive_id": aid,
        "start_date": 1700000000,
        "collation_count": 3,
        "snapshot": {
            "page_name": "Loja X",
            "link_url": "https://loja.com/oferta",
            "cta_text": "Saiba mais",
            "title": "Título",
            "body": {"text": "Copy do anúncio"},
            "videos": [{"video_hd_url": "https://cdn/v1.mp4?x=1"}],
            "images": [],
        },
    }
    base.update(extra)
    return base


def test_montar_url_por_termo():
    url = montar_url(termo="receita fit")
    assert url.startswith("https://www.facebook.com/ads/library/?active_status=active")
    assert "country=BR" in url
    assert "q=receita%20fit" in url
    assert "search_type=keyword_unordered" in url
    assert "sort_data[mode]=total_impressions&sort_data[direction]=desc" in url


def test_montar_url_frase_exata_e_pais():
    url = montar_url(termo="jejum", frase_exata=True, pais="ALL")
    assert "search_type=keyword_exact_phrase" in url and "country=ALL" in url


def test_montar_url_por_dominio_tira_protocolo_e_poe_barra():
    url = montar_url(dominio="https://www.site.com.br/")
    assert "q=www.site.com.br%2F" in url


@pytest.mark.parametrize("kwargs", [{}, {"termo": "a", "dominio": "b.com"}])
def test_montar_url_exige_um_criterio(kwargs):
    with pytest.raises(ValueError):
        montar_url(**kwargs)


def test_colher_normaliza_e_deduplica_preservando_ordem():
    c = Coletor()
    c.colher({"data": [_ad("2"), {"deep": [_ad("1")]}, _ad("2")]})
    assert [a["id"] for a in c.anuncios] == ["2", "1"]
    a = c.anuncios[0]
    assert a == {
        "id": "2", "pagina": "Loja X", "inicio": 1700000000, "repeticoes": 3,
        "cta": "Saiba mais", "link": "https://loja.com/oferta", "titulo": "Título",
        "texto": "Copy do anúncio", "videos": ["https://cdn/v1.mp4?x=1"], "imagens": [],
        "midia": "video",
    }


def test_colher_aceita_camel_case_e_imagem():
    c = Coletor()
    c.colher({
        "adArchiveID": 99, "startDate": "1700000000", "collationCount": None,
        "snapshot": {"page_name": "P", "images": [{"originalImageUrl": "https://i/1.jpg"}],
                     "cards": [{"title": "Card", "body": "Texto do card", "link_url": "https://c.com"}]},
    })
    a = c.anuncios[0]
    assert (a["id"], a["inicio"], a["repeticoes"], a["midia"]) == ("99", 1700000000, None, "imagem")
    assert (a["titulo"], a["texto"], a["link"]) == ("Card", "Texto do card", "https://c.com")


def test_colher_ignora_objeto_sem_snapshot_e_lixo():
    c = Coletor()
    c.colher({"ad_archive_id": "1"})
    c.colher([None, 3, "x", {"snapshot": {}}])
    assert c.anuncios == []


def test_colher_html_le_scripts_json_e_tolera_bloco_quebrado():
    html = (
        '<script type="application/json" data-sjs>' + json.dumps({"x": _ad("7")}) + "</script>"
        '<script type="application/json">{quebrado</script>'
    )
    c = Coletor()
    c.colher_html(html)
    assert [a["id"] for a in c.anuncios] == ["7"]


def test_colher_graphql_divide_por_linha():
    texto = "lixo\n" + json.dumps({"a": _ad("1")}) + "\n" + json.dumps({"b": _ad("2")})
    c = Coletor()
    c.colher_graphql(texto)
    assert [a["id"] for a in c.anuncios] == ["1", "2"]


def test_colher_suporta_json_muito_profundo():
    raiz = _ad("fundo")
    for _ in range(3000):
        raiz = {"n": raiz}
    c = Coletor()
    c.colher(raiz)
    assert [a["id"] for a in c.anuncios] == ["fundo"]
