# tests/test_pagina_config_publicar.py
import json

import pytest

import pagina_config
import pagina_conteudo as pc
import pagina_publicar
from nucleo.netlify import NetlifyErro


def _proj(tmp_path, checkout="https://c.com", com_site=True):
    p = tmp_path / "proj"
    pagina = p / "pagina"
    pagina.mkdir(parents=True)
    (pagina / "conteudo.json").write_text(json.dumps(
        {"hero": {"headline": "Oi"}, "planos": {"basico": {"checkoutUrl": checkout, "precoPor": "R$ 9"}}}))
    if com_site:
        (pagina / "site").mkdir()
        (pagina / "site" / "index.html").write_text("<h1>oi</h1>")
    return p


def test_config_definir_e_mostrar(tmp_path, capsys):
    p = _proj(tmp_path)
    assert pagina_config.main(["--projeto", str(p), "--definir", "paleta=verde-branco",
                               "--definir", "pixel_meta=123456789012", "--definir", "seo_titulo=A=B"]) == 0
    cfg = pc.ler_config(p / "pagina")
    assert (cfg["paleta"], cfg["pixel_meta"], cfg["seo_titulo"]) == ("verde-branco", "123456789012", "A=B")
    capsys.readouterr()
    assert pagina_config.main(["--projeto", str(p)]) == 0
    assert "verde-branco" in capsys.readouterr().out


def test_config_valor_invalido_nao_grava_nada(tmp_path, capsys):
    p = _proj(tmp_path)
    assert pagina_config.main(["--projeto", str(p), "--definir", "paleta=preto-dourado",
                               "--definir", "pixel_meta=abc"]) == 1
    assert "Pixel" in capsys.readouterr().err
    assert pc.ler_config(p / "pagina")["paleta"] == pc.PALETA_PADRAO


def test_config_sem_igual_e_head_arquivo(tmp_path, capsys):
    p = _proj(tmp_path)
    assert pagina_config.main(["--projeto", str(p), "--definir", "paleta"]) == 1
    head = tmp_path / "utmify.html"
    head.write_text('<script src="https://cdn.utmify.com.br/x.js"></script>')
    assert pagina_config.main(["--projeto", str(p), "--head-arquivo", str(head)]) == 0
    assert "utmify" in pc.ler_config(p / "pagina")["head_html"]
    assert pagina_config.main(["--projeto", str(p), "--head-arquivo", str(tmp_path / "nao.html")]) == 1


def test_config_lista_paletas(tmp_path, capsys):
    assert pagina_config.main(["--projeto", str(_proj(tmp_path)), "--paletas"]) == 0
    out = capsys.readouterr().out
    assert "preto-dourado" in out and "Preto e dourado" in out


def test_config_preserva_site_id(tmp_path):
    p = _proj(tmp_path)
    pc.salvar_config(p / "pagina", dict(pc.CONFIG_PADRAO, site_id="s1", url="https://x"))
    pagina_config.main(["--projeto", str(p), "--definir", "paleta=grafite-ciano"])
    cfg = pc.ler_config(p / "pagina")
    assert (cfg["site_id"], cfg["url"]) == ("s1", "https://x")


def test_publicar_sem_token_sai_3_com_instrucoes(ambiente, tmp_path, capsys):
    p = _proj(tmp_path)
    assert pagina_publicar.main(["--projeto", str(p)]) == 3
    out = capsys.readouterr().out
    assert "app.netlify.com/drop" in out and str(p / "pagina" / "site") in out


def test_publicar_ok_salva_site_id_e_republica(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")
    chamadas = []

    def falso(token, pasta, site_id=None):
        chamadas.append((token, pasta, site_id))
        return {"site_id": "s1", "url": "https://abc.netlify.app"}

    monkeypatch.setattr(pagina_publicar, "publicar_pasta", falso)
    assert pagina_publicar.main(["--projeto", str(p)]) == 0
    assert "https://abc.netlify.app" in capsys.readouterr().out
    assert pc.ler_config(p / "pagina")["site_id"] == "s1"
    pagina_publicar.main(["--projeto", str(p)])
    assert chamadas[0] == ("tok", p / "pagina" / "site", None)
    assert chamadas[1][2] == "s1"


def test_publicar_sem_site_ou_sem_checkout(ambiente, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")
    p = _proj(tmp_path, com_site=False)
    assert pagina_publicar.main(["--projeto", str(p)]) == 1
    assert "pagina_render" in capsys.readouterr().err
    p2 = _proj(tmp_path / "b", checkout="")
    assert pagina_publicar.main(["--projeto", str(p2)]) == 1
    assert "checkout" in capsys.readouterr().err


def test_publicar_erro_netlify_amigavel(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")

    def quebra(token, pasta, site_id=None):
        raise NetlifyErro("A Netlify recusou o token.")

    monkeypatch.setattr(pagina_publicar, "publicar_pasta", quebra)
    assert pagina_publicar.main(["--projeto", str(p)]) == 1
    err = capsys.readouterr().err
    assert "recusou o token" in err and "Traceback" not in err


def test_publicar_argumento_faltando(capsys):
    assert pagina_publicar.main([]) == 1
    assert "--projeto" in capsys.readouterr().err
