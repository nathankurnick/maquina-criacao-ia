import json
from datetime import date, datetime, timezone

import pytest

import ofertas as of

HOJE = date(2026, 9, 28)


def _epoch(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def _ad(aid, link="https://loja.com/a", texto="Copy grande o suficiente", pagina="Loja",
        inicio=date(2026, 8, 1), rep=1, video=None, imagem=None):
    videos = [video] if video else []
    imagens = [imagem] if imagem else []
    return {"id": aid, "pagina": pagina, "inicio": _epoch(inicio) if inicio else None,
            "repeticoes": rep, "cta": "", "link": link, "titulo": "", "texto": texto,
            "videos": videos, "imagens": imagens,
            "midia": "video" if videos else ("imagem" if imagens else "nenhuma")}


@pytest.mark.parametrize("link,chave", [
    ("https://www.loja.com.br/oferta?utm=1", "loja.com.br"),
    ("loja.com.br/x", "loja.com.br"),
    ("https://pay.kiwify.com.br/AbC123?x", "kiwify.com.br/AbC123"),
    ("https://go.hotmart.com/Q123/", "hotmart.com/Q123"),
    ("https://wa.me/5511999999999", "wa.me/5511999999999"),
    ("https://l.facebook.com/l.php?u=https%3A%2F%2Floja.com%2Fp&h=x", "loja.com"),
    ("https://www.facebook.com/pagina", None),
    ("https://instagram.com/x", None),
    ("", None),
])
def test_chave_oferta(link, chave):
    assert of.chave_oferta(link) == chave


def test_parece_isca_precisa_de_dois_sinais():
    assert of.parece_isca(_ad("1", link="https://trk.abc.com/x", texto="."))
    assert of.parece_isca(_ad("2", link="https://oferta.click/x", texto=""))
    assert of.parece_isca(_ad("3", link="", texto="."))
    assert not of.parece_isca(_ad("4", link="https://oferta.click/x"))
    assert not of.parece_isca(_ad("5", link="https://loja.com", texto="."))


def test_dias_no_ar():
    assert of.dias_no_ar(_epoch(date(2026, 8, 29)), HOJE) == 30
    assert of.dias_no_ar(None, HOJE) is None


@pytest.mark.parametrize("volume,dias,selo", [
    (20, 30, "🔥 escalada"), (40, 10, "📈 validando"), (2, 14, "📈 validando"),
    (5, None, "📈 validando"), (1, 3, "🌱 em teste"),
])
def test_termometro_selos(volume, dias, selo):
    assert of.termometro(volume, dias)[1] == selo


def test_termometro_pontuacao_satura_em_90_dias():
    assert of.termometro(10, 30)[0] == 20.0
    assert of.termometro(10, 400)[0] == 40.0
    assert of.termometro(10, None)[0] == 10.0


def test_analisar_agrupa_conta_e_ranqueia():
    anuncios = [
        _ad("1", link="https://a.com/x", video="https://cdn/v1.mp4?q", rep=10, pagina="A",
            inicio=date(2026, 6, 1), texto="Texto repetido da oferta A"),
        _ad("2", link="https://a.com/y", video="https://cdn/v1.mp4?z", rep=20, pagina="A",
            texto="Texto repetido da oferta A"),
        _ad("3", link="https://a.com/z", imagem="https://cdn/i1.jpg", rep=None, pagina="A2"),
        _ad("4", link="https://b.com", video="https://cdn/v9.mp4", rep=2, pagina="B",
            inicio=date(2026, 9, 20)),
        _ad("5", link="https://trk.lixo.info/x", texto="."),
        _ad("6", link="", texto="Sem link nenhum aqui"),
    ]
    r = of.analisar(anuncios, HOJE)
    assert (r["total_anuncios"], r["descartados_isca"], r["sem_link"]) == (6, 1, 1)
    a, b = r["ofertas"]
    assert a["chave"] == "a.com"
    assert (a["anuncios"], a["criativos"], a["volume"]) == (3, 2, 21)
    assert a["dias"] == (HOJE - date(2026, 6, 1)).days
    assert a["anunciantes"] == ["A", "A2"]
    assert a["midia"] == "vídeo"
    assert a["posicao"] == 1
    assert a["textos"][0] == "Texto repetido da oferta A"
    assert a["link"] == "https://a.com/x"
    assert a["selo"] == "🔥 escalada"
    assert b["chave"] == "b.com" and b["volume"] == 2 and b["selo"] == "🌱 em teste"


def test_midia_misto_quando_nenhum_formato_tem_60_por_cento():
    anuncios = [_ad("1", video="https://c/v1.mp4"), _ad("2", imagem="https://c/i.jpg")]
    assert of.analisar(anuncios, HOJE)["ofertas"][0]["midia"] == "misto"


def test_tabela_markdown_limita_e_formata():
    anuncios = [_ad(str(i), link=f"https://o{i}.com") for i in range(12)]
    tabela = of.tabela_markdown(of.analisar(anuncios, HOJE)["ofertas"], limite=10)
    linhas = tabela.strip().splitlines()
    assert linhas[0].startswith("| # | Oferta |")
    assert len(linhas) == 12  # cabeçalho + separador + 10


def test_main_grava_arquivos(tmp_path, capsys):
    entrada = tmp_path / "anuncios.json"
    entrada.write_text(json.dumps([_ad("1", link="https://a.com", rep=30, inicio=date(2026, 7, 1))]))
    saida = tmp_path / "out"
    assert of.main([str(entrada), "--saida", str(saida), "--hoje", "2026-09-28"]) == 0
    dados = json.loads((saida / "ofertas.json").read_text())
    assert dados["ofertas"][0]["chave"] == "a.com"
    assert (saida / "ofertas.md").read_text().startswith("| # | Oferta |")
    assert "a.com" in capsys.readouterr().out


def test_main_arquivo_invalido_mensagem_amigavel(tmp_path, capsys):
    ruim = tmp_path / "x.json"
    ruim.write_text("{nao é json")
    assert of.main([str(ruim), "--saida", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "Não consegui ler" in err and "Traceback" not in err
    assert of.main([str(tmp_path / "nao-existe.json"), "--saida", str(tmp_path)]) == 1


@pytest.mark.parametrize("link,chave", [
    ("https://pay.hotmart.com/A123", "hotmart.com/A123"),
    ("https://go.hotmart.com/A123?ap=1", "hotmart.com/A123"),
    ("https://hotmart.com/pt-br/marketplace/produtos/x", "hotmart.com/x"),
    ("https://hotmart.com/en/product/abc", "hotmart.com/abc"),
    ("https://pay.kiwify.com.br/AbC", "kiwify.com.br/AbC"),
    ("https://bit.ly/3xYz", "bit.ly/3xYz"),
    ("https://bit.ly/aaa", "bit.ly/aaa"),
    ("https://t.co/Qw1", "t.co/Qw1"),
    ("https://[bad/x", None),
])
def test_chave_oferta_plataformas_e_encurtadores(link, chave):
    assert of.chave_oferta(link) == chave


def test_encurtadores_distintos_nao_colapsam():
    assert of.chave_oferta("https://bit.ly/a") != of.chave_oferta("https://bit.ly/b")


def test_hoje_invalido_mensagem_amigavel(tmp_path, capsys):
    e = tmp_path / "a.json"
    e.write_text("[]")
    assert of.main([str(e), "--saida", str(tmp_path), "--hoje", "ontem"]) == 1
    err = capsys.readouterr().err
    assert "--hoje" in err and "Traceback" not in err


def test_anuncios_malformados_nao_quebram(tmp_path, capsys):
    ruins = [
        "texto", 5, None, [],
        {"link": "https://a.com/x", "texto": "Texto grande o bastante", "repeticoes": "abc", "inicio": "x"},
        {"id": "9", "link": "https://a.com/y", "texto": "Texto grande o bastante", "repeticoes": 3.7,
         "inicio": 10**30},
        {"id": "8", "link": "https://a.com/z", "texto": "Texto grande o bastante", "repeticoes": 0,
         "inicio": -10**30},
        {"id": "7", "link": "https://a.com/w", "texto": "Texto grande o bastante", "repeticoes": None,
         "inicio": True},
    ]
    r = of.analisar(ruins, HOJE)
    assert r["invalidos"] == 4
    assert r["ofertas"][0]["chave"] == "a.com"
    assert r["ofertas"][0]["dias"] is None
    e = tmp_path / "a.json"
    e.write_text(json.dumps(ruins))
    assert of.main([str(e), "--saida", str(tmp_path / "o"), "--hoje", "2026-09-28"]) == 0
    assert "inválidos" in capsys.readouterr().out


def test_sem_invalidos_nao_menciona(tmp_path, capsys):
    e = tmp_path / "a.json"
    e.write_text(json.dumps([_ad("1")]))
    of.main([str(e), "--saida", str(tmp_path / "o"), "--hoje", "2026-09-28"])
    assert "inválidos" not in capsys.readouterr().out


def test_tabela_escapa_pipe_e_quebra_de_linha():
    o = {"chave": "a|b", "anunciantes": ["Lo|ja\nX\nY".replace("\\n", "\n")], "volume": 1, "dias": None,
         "midia": "vídeo", "selo": "s", "pontuacao": 1.0, "link": "https://a.com/?q=1|2"}
    linha = of.tabela_markdown([o]).splitlines()[2]
    assert "a\\|b" in linha and "Lo\\|ja" in linha and "\n" not in linha
    assert linha.replace("\\|", "").count("|") == 9
    assert "| Volume |" in of.tabela_markdown([o])


def test_campos_de_tipo_errado_nao_quebram():
    base = {"link": "https://a.com/x", "texto": "Texto grande o bastante"}
    ruins = [
        {**base, "id": "1", "pagina": ["A"]},
        {**base, "id": "2", "pagina": {"n": 1}},
        {**base, "id": "3", "videos": [None, 5]},
        {**base, "id": "4", "videos": 5},
        {**base, "id": "5", "midia": ["x"]},
        {**base, "id": "6", "videos": ["", "https://c/v.mp4"], "imagens": "x"},
    ]
    r = of.analisar(ruins, HOJE)
    o = r["ofertas"][0]
    assert o["anuncios"] == 6 and o["anunciantes"] == []
    assert o["midia"] in ("vídeo", "imagem", "misto")
    assert o["criativos"] == 6 and o["volume"] == 6


@pytest.mark.parametrize("link,chave", [
    ("https://api.whatsapp.com/send?phone=5511999&text=oi", "whatsapp.com/5511999"),
    ("https://api.whatsapp.com/send", "whatsapp.com/send"),
    ("https://wa.me/5511999", "wa.me/5511999"),
])
def test_chave_whatsapp(link, chave):
    assert of.chave_oferta(link) == chave


def test_whatsapp_sem_telefone_separa_por_anunciante():
    def ad(i, pagina):
        return {"id": str(i), "pagina": pagina, "link": "https://api.whatsapp.com/send",
                "texto": f"texto {i}", "inicio": "2026-01-01"}
    r = of.analisar([ad(1, "A"), ad(2, "B")], date(2026, 9, 1))
    assert sorted(o["chave"] for o in r["ofertas"]) == ["whatsapp:A", "whatsapp:B"]


def test_whatsapp_sem_pagina_nao_junta_anuncios():
    def ad(i):
        return {"id": str(i), "pagina": "", "link": "https://wa.me/", "texto": f"t{i}", "inicio": "2026-01-01"}
    r = of.analisar([ad(1), ad(2)], date(2026, 9, 1))
    assert sorted(o["chave"] for o in r["ofertas"]) == ["whatsapp:?1", "whatsapp:?2"]
