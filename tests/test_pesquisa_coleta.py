import json

import pytest

from coleta import Coletor, montar_url


def _ad(aid, **extra):
    base = {
        "ad_archive_id": aid, "page_id": "555",
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
        "midia": "video", "pagina_id": "555",
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


def test_colher_html_pula_bloco_profundo_demais_e_segue():
    fundo = '{"a":' * 5000 + "1" + "}" * 5000
    html = (
        '<script type="application/json">' + fundo + "</script>"
        '<script type="application/json">' + json.dumps({"x": _ad("ok")}) + "</script>"
    )
    c = Coletor()
    c.colher_html(html)
    assert [a["id"] for a in c.anuncios] == ["ok"]


def test_colher_graphql_pula_pedaco_profundo_demais_e_segue():
    fundo = '{"a":' * 5000 + "1" + "}" * 5000
    c = Coletor()
    c.colher_graphql(fundo + "\n" + json.dumps({"x": _ad("ok")}))
    assert [a["id"] for a in c.anuncios] == ["ok"]


def test_colher_tolera_midia_com_tipo_errado():
    estranho = _ad("estranho")
    estranho["snapshot"].update({"videos": 5, "images": "x", "cards": True})
    c = Coletor()
    c.colher({"a": estranho, "b": _ad("normal")})
    por_id = {a["id"]: a for a in c.anuncios}
    assert set(por_id) == {"estranho", "normal"}
    assert por_id["estranho"]["videos"] == [] and por_id["estranho"]["imagens"] == []
    assert por_id["estranho"]["midia"] == "nenhuma"


def test_colher_pula_anuncio_que_quebra_a_normalizacao(monkeypatch):
    import coleta
    original = coleta._normalizar

    def falha_no_ruim(obj, snap, aid):
        if aid == "ruim":
            raise RuntimeError("boom")
        return original(obj, snap, aid)

    monkeypatch.setattr(coleta, "_normalizar", falha_no_ruim)
    c = Coletor()
    c.colher([_ad("ruim"), _ad("bom")])
    assert [a["id"] for a in c.anuncios] == ["bom"]
    assert "ruim" not in c._vistos


def test_colher_coage_campos_de_texto_pra_str():
    ad = _ad("t")
    ad["snapshot"].update({"page_name": {"x": 1}, "cta_text": ["a"], "link_url": 12, "title": {"y": 2}})
    c = Coletor()
    c.colher(ad)
    a = c.anuncios[0]
    assert a["pagina"] == "" and a["cta"] == "" and a["link"] == "12" and a["titulo"] == ""


def test_coletor_declara_estado_inicial():
    c = Coletor()
    assert c.cancelado is False and c.erro_nome == "" and c.login_wall is False


def test_texto_nao_string_e_coagido():
    c = Coletor()
    c.colher({"ad_archive_id": "1", "snapshot": {"body": {"text": {"a": 1}}, "cards": [{"body": 42}]}})
    assert c.anuncios[0]["texto"] == ""
    c.colher({"ad_archive_id": "2", "snapshot": {"body": {"text": 12345}}})
    assert c.anuncios[1]["texto"] == "12345"
