# tests/test_pagina_config_publicar.py
import json

import pytest

import pagina_config
import pagina_conteudo as pc
import pagina_publicar
import pagina_render
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


def test_publicar_sem_conteudo_ou_sem_checkout(ambiente, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")
    p = _proj(tmp_path, com_site=False)
    (p / "pagina" / "conteudo.json").unlink()
    assert pagina_publicar.main(["--projeto", str(p)]) == 1
    assert "conteudo.json" in capsys.readouterr().err
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


def test_publicar_nucleo_ausente_sai_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pagina_publicar, "NUCLEO_OK", False)
    assert pagina_publicar.main(["--projeto", str(_proj(tmp_path))]) == 1
    assert "instalar.sh" in capsys.readouterr().err


def test_publicar_import_do_nucleo_falho_marca_flag(monkeypatch):
    import importlib
    import sys as _s
    for nome in [n for n in _s.modules if n == "nucleo" or n.startswith("nucleo.")]:
        monkeypatch.setitem(_s.modules, nome, None)  # import vira ImportError
    try:
        mod = importlib.reload(pagina_publicar)
        assert mod.NUCLEO_OK is False
    finally:
        monkeypatch.undo()
        importlib.reload(pagina_publicar)
    assert pagina_publicar.NUCLEO_OK is True


def test_publicar_falha_ao_salvar_config_ainda_avisa_no_ar(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")
    monkeypatch.setattr(pagina_publicar, "publicar_pasta",
                        lambda t, pasta, site_id=None: {"site_id": "s9", "url": "https://z.netlify.app"})

    def quebra(*a, **k):
        raise OSError("disco")

    monkeypatch.setattr(pagina_publicar, "salvar_config", quebra)
    assert pagina_publicar.main(["--projeto", str(p)]) == 0
    out = capsys.readouterr().out
    assert "No ar: https://z.netlify.app" in out and "s9" in out and "anote" in out


def test_publicar_ctrl_c_sai_130(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")

    def ctrl_c(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(pagina_publicar, "publicar_pasta", ctrl_c)
    assert pagina_publicar.main(["--projeto", str(p)]) == 130
    err = capsys.readouterr().err
    assert "Cancelado" in err and "Traceback" not in err


def test_publicar_log_quebrado_nao_esconde_mensagem(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")

    def boom(*a, **k):
        raise RuntimeError("x")

    def log_quebra(_):
        raise OSError("sem log")

    monkeypatch.setattr(pagina_publicar, "publicar_pasta", boom)
    monkeypatch.setattr(pagina_publicar, "registrar_log", log_quebra)
    assert pagina_publicar.main(["--projeto", str(p)]) == 1
    assert "Algo deu errado" in capsys.readouterr().err


def test_publicar_site_id_novo_sobrescreve_o_salvo(ambiente, tmp_path, monkeypatch):
    p = _proj(tmp_path)
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")
    pc.salvar_config(p / "pagina", dict(pc.CONFIG_PADRAO, site_id="velho", url="https://velho"))
    monkeypatch.setattr(pagina_publicar, "publicar_pasta",
                        lambda t, pasta, site_id=None: {"site_id": "novo", "url": "https://novo.netlify.app"})
    assert pagina_publicar.main(["--projeto", str(p)]) == 0
    cfg = pc.ler_config(p / "pagina")
    assert (cfg["site_id"], cfg["url"]) == ("novo", "https://novo.netlify.app")


def test_publicar_sem_token_nao_chama_netlify(ambiente, tmp_path, monkeypatch):
    def nunca(*a, **k):
        raise AssertionError("não deveria chamar")

    monkeypatch.setattr(pagina_publicar, "publicar_pasta", nunca)
    assert pagina_publicar.main(["--projeto", str(_proj(tmp_path))]) == 3


def test_config_ctrl_c_sai_130(tmp_path, monkeypatch, capsys):
    def ctrl_c(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(pagina_config, "ler_config", ctrl_c)
    assert pagina_config.main(["--projeto", str(_proj(tmp_path))]) == 130
    err = capsys.readouterr().err
    assert "Cancelado" in err and "Traceback" not in err


def test_config_head_arquivo_binario_e_grande(tmp_path, capsys):
    p = _proj(tmp_path)
    binario = tmp_path / "b.html"
    binario.write_bytes(b"\xff\xfe\x00\xff")
    assert pagina_config.main(["--projeto", str(p), "--head-arquivo", str(binario)]) == 1
    err = capsys.readouterr().err
    assert "Não consegui ler" in err and "Traceback" not in err
    grande = tmp_path / "g.html"
    grande.write_text("a" * (100 * 1024 + 1))
    assert pagina_config.main(["--projeto", str(p), "--head-arquivo", str(grande)]) == 1
    assert "100 KB" in capsys.readouterr().err
    assert pc.ler_config(p / "pagina")["head_html"] == ""


def _fake_ok(monkeypatch, url="https://abc.netlify.app"):
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")
    monkeypatch.setattr(pagina_publicar, "publicar_pasta",
                        lambda t, pasta, site_id=None: {"site_id": "s1", "url": url})


def test_publicar_avisa_quando_o_endereco_mudou(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    _fake_ok(monkeypatch, "https://novo.netlify.app")
    pc.salvar_config(p / "pagina", dict(pc.CONFIG_PADRAO, url="https://velho.netlify.app"))
    assert pagina_publicar.main(["--projeto", str(p)]) == 0
    out = capsys.readouterr().out
    assert ("⚠️ O endereço da página mudou: https://velho.netlify.app → https://novo.netlify.app. "
            "Atualize o link nos seus anúncios.") in out


def test_publicar_nao_avisa_se_endereco_igual_ou_primeira_vez(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    _fake_ok(monkeypatch)
    pagina_publicar.main(["--projeto", str(p)])
    assert "mudou" not in capsys.readouterr().out
    pagina_publicar.main(["--projeto", str(p)])
    assert "mudou" not in capsys.readouterr().out


def test_config_definir_url_https_e_site_id_nao_editavel(tmp_path, capsys):
    p = _proj(tmp_path)
    assert pagina_config.main(["--projeto", str(p), "--definir", "url=https://x.netlify.app"]) == 0
    assert pc.ler_config(p / "pagina")["url"] == "https://x.netlify.app"
    assert pagina_config.main(["--projeto", str(p), "--definir", "url=http://x.com"]) == 1
    assert pagina_config.main(["--projeto", str(p), "--definir", "site_id=abc"]) == 1
    assert pc.ler_config(p / "pagina")["site_id"] == ""


def test_exit3_instrucoes_login_antes_de_arrastar(ambiente, tmp_path, capsys):
    p = _proj(tmp_path)
    assert pagina_publicar.main(["--projeto", str(p)]) == 3
    out = capsys.readouterr().out
    assert "ANTES de arrastar" in out and "cerca de 1 hora" in out
    assert out.index("1. Entre") < out.index("app.netlify.com/drop") < out.index("3. Arraste") < out.index("4. Copie")


def test_publicar_remonta_antes_de_publicar(ambiente, tmp_path, monkeypatch):
    p = _proj(tmp_path)
    _fake_ok(monkeypatch)
    vistos = []
    monkeypatch.setattr(pagina_publicar, "publicar_pasta",
                        lambda t, pasta, site_id=None: vistos.append((pasta / "index.html").read_text())
                        or {"site_id": "s1", "url": "https://abc.netlify.app"})
    pagina_render.main(["--projeto", str(p)])
    (p / "pagina" / "conteudo.json").write_text(json.dumps(
        {"hero": {"headline": "Headline Nova"}, "planos": {"basico": {"checkoutUrl": "https://c.com",
                                                                        "precoPor": "R$ 9"}}}))
    assert pagina_publicar.main(["--projeto", str(p)]) == 0
    assert "Headline Nova" in vistos[0]


def test_publicar_imprime_avisos_do_render(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    _fake_ok(monkeypatch)
    assert pagina_publicar.main(["--projeto", str(p)]) == 0
    assert "⚠️ depoimentos" in capsys.readouterr().out


def test_publicar_falha_no_render_aborta_com_mensagem(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    _fake_ok(monkeypatch)
    (p / "pagina" / "conteudo.json").write_text("{ quebrado")
    assert pagina_publicar.main(["--projeto", str(p)]) == 1
    assert "erro de formatação JSON" in capsys.readouterr().err


def test_render_config_publicar_com_pasta_pagina_propria(ambiente, tmp_path, monkeypatch, capsys):
    p = _proj(tmp_path)
    up = p / "funil" / "upsell"
    up.mkdir(parents=True)
    (up / "conteudo.json").write_text(json.dumps(
        {"hero": {"headline": "Upsell Legal"}, "planos": {"basico": {"checkoutUrl": "https://c.com/up",
                                                                      "precoPor": "R$ 9"}}}))
    assert pagina_config.main(["--projeto", str(p), "--pagina", str(up), "--definir", "paleta=verde-branco"]) == 0
    assert pc.ler_config(up)["paleta"] == "verde-branco"
    assert pc.ler_config(p / "pagina")["paleta"] == pc.PALETA_PADRAO
    assert pagina_render.main(["--projeto", str(p), "--pagina", str(up)]) == 0
    assert "Upsell Legal" in (up / "site" / "index.html").read_text()
    vistos = []
    monkeypatch.setenv("NETLIFY_TOKEN", "tok")
    monkeypatch.setattr(pagina_publicar, "publicar_pasta",
                        lambda t, pasta, site_id=None: vistos.append(pasta)
                        or {"site_id": "u1", "url": "https://up.netlify.app"})
    assert pagina_publicar.main(["--projeto", str(p), "--pagina", str(up)]) == 0
    assert vistos == [up / "site"]
    assert pc.ler_config(up)["site_id"] == "u1" and pc.ler_config(p / "pagina")["site_id"] == ""
