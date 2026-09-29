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
    ("https://pay.kiwify.com.br/AbC123?x", "pay.kiwify.com.br/AbC123"),
    ("https://go.hotmart.com/Q123/", "go.hotmart.com/Q123"),
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
