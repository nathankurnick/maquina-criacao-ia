import json

import pytest

import capturar


def test_extrair_dados_precos_checkout_garantia():
    texto = ("De R$ 197,00 por apenas R$ 47,90 à vista ou 12x de R$ 4,90. "
             "Você tem garantia incondicional de 7 dias. R$ 47,90")
    links = ["https://pay.kiwify.com.br/abc", "https://site.com/sobre",
             "https://pay.hotmart.com/X1?off=1", "https://pay.kiwify.com.br/abc"]
    d = capturar.extrair_dados(texto, links)
    assert d["precos"] == ["R$ 197,00", "R$ 47,90", "R$ 4,90"]
    assert d["links_checkout"] == ["https://pay.kiwify.com.br/abc", "https://pay.hotmart.com/X1?off=1"]
    assert d["garantia"] == "garantia incondicional de 7 dias"


def test_extrair_dados_vazio():
    assert capturar.extrair_dados("", []) == {"precos": [], "links_checkout": [], "garantia": ""}


def test_extrair_dados_limite_de_10():
    texto = " ".join(f"R$ {i},00" for i in range(1, 20))
    links = [f"https://pay.kiwify.com.br/{i}" for i in range(20)]
    d = capturar.extrair_dados(texto, links)
    assert len(d["precos"]) == 10 and len(d["links_checkout"]) == 10


def test_main_erro_amigavel(tmp_path, monkeypatch, capsys):
    def quebra(url, saida):
        raise RuntimeError("net::ERR_NAME_NOT_RESOLVED")
    monkeypatch.setattr(capturar, "capturar", quebra)
    assert capturar.main(["--url", "https://nao-existe.invalid", "--saida", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "Não consegui abrir" in err and "Traceback" not in err
    assert "a página não abriu" in err and "mande prints e o texto" in err


@pytest.mark.parametrize("exc,trecho", [
    (ModuleNotFoundError("No module named 'playwright'"), "instalar.sh"),
    (RuntimeError("BrowserType.launch: Executable doesn't exist at /x/chromium"), "instalar.sh"),
    (TimeoutError("Timeout 45000ms exceeded"), "a página não abriu"),
    (ValueError("qualquer coisa"), "mande prints e o texto"),
])
def test_main_mensagem_por_causa(tmp_path, monkeypatch, capsys, exc, trecho):
    def quebra(url, saida):
        raise exc
    monkeypatch.setattr(capturar, "capturar", quebra)
    assert capturar.main(["--url", "https://x.com", "--saida", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert trecho in err and "mande prints e o texto" in err and "Traceback" not in err


def test_main_ctrl_c(tmp_path, monkeypatch, capsys):
    def cancela(url, saida):
        raise KeyboardInterrupt
    monkeypatch.setattr(capturar, "capturar", cancela)
    assert capturar.main(["--url", "https://x.com", "--saida", str(tmp_path)]) == 130
    err = capsys.readouterr().err
    assert "Captura cancelada." in err and "Traceback" not in err


def test_main_argumentos_invalidos_em_portugues(capsys):
    assert capturar.main(["--saida", "x"]) == 1
    err = capsys.readouterr().err
    assert "Comando inválido" in err and "usage" not in err.lower()
    assert capturar.main([]) == 1
    assert capturar.main(["--url"]) == 1
    assert capturar.main(["--url", "u", "--saida", "x", "--foo"]) == 1


def test_main_saida_nao_gravavel(tmp_path, monkeypatch, capsys):
    arquivo = tmp_path / "arquivo"
    arquivo.write_text("x")
    chamou = []
    monkeypatch.setattr(capturar, "capturar", lambda u, s: chamou.append(1))
    assert capturar.main(["--url", "https://x.com", "--saida", str(arquivo / "sub")]) == 1
    err = capsys.readouterr().err
    assert "pasta de saída" in err and not chamou


def test_main_sucesso(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(capturar, "capturar", lambda u, s: {
        "url": u, "titulo": "T", "precos": ["R$ 1,00"], "links_checkout": [], "garantia": ""})
    assert capturar.main(["--url", "https://x.com", "--saida", str(tmp_path / "o")]) == 0
    assert "T" in capsys.readouterr().out


def test_capturar_pagina_local_de_verdade(tmp_path):
    pytest.importorskip("playwright")
    html = tmp_path / "lp.html"
    html.write_text(
        "<html><head><title>Oferta Teste</title></head><body>"
        "<h1>Método X</h1><p>Por R$ 37,00 com garantia de 30 dias.</p>"
        '<a href="https://pay.kiwify.com.br/ZZ">Comprar</a>'
        + "<p>linha</p>" * 200 + "</body></html>", encoding="utf-8")
    try:
        dados = capturar.capturar(html.as_uri(), tmp_path / "out")
    except Exception as e:  # navegador não instalado na máquina de dev
        pytest.skip(f"Chromium do Playwright indisponível: {e}")
    out = tmp_path / "out"
    assert dados["titulo"] == "Oferta Teste"
    assert dados["precos"] == ["R$ 37,00"]
    assert dados["links_checkout"] == ["https://pay.kiwify.com.br/ZZ"]
    assert "Método X" in (out / "pagina.txt").read_text()
    assert (out / "pagina.png").stat().st_size > 0 and (out / "dobra.png").stat().st_size > 0
    assert json.loads((out / "dados.json").read_text())["garantia"] == "garantia de 30 dias"
