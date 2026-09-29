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


@pytest.mark.parametrize("texto,esperado", [
    ("por R$1997,00 hoje", ["R$ 1997,00"]),
    ("R$ 1.997 no total", ["R$ 1.997"]),
    ("apenas R$47", ["R$ 47"]),
    ("12x de R$ 19,70", ["R$ 19,70"]),
])
def test_precos_formatos(texto, esperado):
    assert capturar.extrair_dados(texto, [])["precos"] == esperado


@pytest.mark.parametrize("url", [
    "https://pay.hotmart.com/X", "https://go.hotmart.com/Y", "https://pay.kiwify.com.br/Z",
    "https://loja.com/checkout", "https://checkout.loja.com/p", "https://pay.site.com/a",
    "https://payt.com.br/x", "https://ticto.com.br/x",
])
def test_checkout_positivos(url):
    assert capturar.extrair_dados("", [url])["links_checkout"] == [url]


@pytest.mark.parametrize("url", [
    "https://repay.com.br/x", "https://blog.com/checkout-review", "https://paytm.com",
    "https://paypal.com/x", "https://blog.com/hotmart-dicas", "https://site.com/sobre",
])
def test_checkout_negativos(url):
    assert capturar.extrair_dados("", [url])["links_checkout"] == []


@pytest.mark.parametrize("texto,esperado", [
    ("Tem 30 dias de garantia total.", "30 dias de garantia"),
    ("garantia incondicional de 7 (sete) dias", "garantia incondicional de 7 (sete) dias"),
    ("Oferecemos garantia de 1 ano.", "garantia de 1 ano"),
    ("garantia de 3 meses", "garantia de 3 meses"),
    ("garantia de 1 mês", "garantia de 1 mês"),
])
def test_garantia_formatos(texto, esperado):
    assert capturar.extrair_dados(texto, [])["garantia"] == esperado


def test_main_remove_saidas_velhas(tmp_path, monkeypatch):
    for n in ("dobra.png", "pagina.png", "pagina-01.png", "pagina-02.png", "pagina.txt", "dados.json"):
        (tmp_path / n).write_text("velho")
    (tmp_path / "outro.txt").write_text("fica")

    def quebra(url, saida):
        raise RuntimeError("net::ERR_FAILED")
    monkeypatch.setattr(capturar, "capturar", quebra)
    assert capturar.main(["--url", "https://x.com", "--saida", str(tmp_path)]) == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["outro.txt"]


def test_mensagem_arquivo(tmp_path, monkeypatch, capsys):
    def quebra(url, saida):
        raise RuntimeError("Page.goto: Download is starting")
    monkeypatch.setattr(capturar, "capturar", quebra)
    assert capturar.main(["--url", "https://x.com/a.pdf", "--saida", str(tmp_path)]) == 1
    assert "esse link é um arquivo, não uma página" in capsys.readouterr().err


class _Pagina:
    def __init__(self, log, erro=None):
        self.log, self.erro, self.url = log, erro, "https://final.com/x"

    def goto(self, url, **kw):
        self.log["goto"].append((url, kw))
        if self.erro:
            raise self.erro

    def wait_for_load_state(self, *a, **kw):
        raise TimeoutError("networkidle")

    def wait_for_timeout(self, ms): pass

    def evaluate(self, js):
        alt = self.log.get("altura", 5000)
        if "scrollBy" in js:
            self.log["scrolls"] = self.log.get("scrolls", 0) + 1
            y = self.log["scrolls"] * 900
            return [y + 800, alt]
        if "scrollWidth" in js:
            return self.log.get("largura", 390)
        if "scrollTo" in js:
            return None
        return alt

    def screenshot(self, path, **kw):
        self.log["shots"].append((path, kw))
        open(path, "wb").write(b"png")

    def inner_text(self, sel): return "texto R$ 10,00"
    def eval_on_selector_all(self, *a): return []
    def title(self): return "T"


def _fake_playwright(monkeypatch, log, erro=None):
    import sys
    import types

    class Ctx:
        def new_page(self): return _Pagina(log, erro)

    class Nav:
        def new_context(self, **kw):
            log["ctx"] = kw
            return Ctx()

        def close(self): pass

    class PW:
        class chromium:
            @staticmethod
            def launch(**kw): return Nav()

        def __enter__(self): return self
        def __exit__(self, *a): return False

    mod = types.ModuleType("playwright.sync_api")
    mod.sync_playwright = lambda: PW()
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", mod)


def test_capturar_navegacao_e_emulacao_movel(tmp_path, monkeypatch):
    log = {"goto": [], "shots": []}
    _fake_playwright(monkeypatch, log)
    dados = capturar.capturar("loja.com/oferta", tmp_path / "o")
    url, kw = log["goto"][0]
    assert len(log["goto"]) == 1 and url == "https://loja.com/oferta"
    assert kw["wait_until"] == "load" and kw["timeout"] == 45000
    c = log["ctx"]
    assert c["viewport"] == {"width": 390, "height": 844} and c["device_scale_factor"] == 2
    assert c["is_mobile"] is True and c["has_touch"] is True and "iPhone" in c["user_agent"]
    assert dados["url_final"] == "https://final.com/x" and dados["altura"] == 5000
    assert dados["prints"] == ["pagina-01.png", "pagina-02.png", "pagina-03.png"]
    clips = [kw["clip"] for path, kw in log["shots"] if "clip" in kw]
    assert all(c["height"] <= 2400 and c["width"] == 390 for c in clips)
    assert sum(c["height"] for c in clips) == 5000
    assert dados["largura"] == 390 and dados["truncada"] is False and dados["altura_capturada"] == 5000


def test_capturar_largura_real_com_cap(tmp_path, monkeypatch):
    log = {"goto": [], "shots": [], "largura": 5000}
    _fake_playwright(monkeypatch, log)
    dados = capturar.capturar("https://x.com", tmp_path / "o")
    assert dados["largura"] == 1280
    assert all(kw["clip"]["width"] == 1280 for path, kw in log["shots"] if "clip" in kw)


def test_capturar_pagina_longa_truncada(tmp_path, monkeypatch):
    log = {"goto": [], "shots": [], "altura": 60000}
    _fake_playwright(monkeypatch, log)
    dados = capturar.capturar("https://x.com", tmp_path / "o")
    assert dados["truncada"] is True and dados["altura"] == 60000
    assert dados["altura_capturada"] == 48000 and len(dados["prints"]) == 20
    assert 50 <= log["scrolls"] <= 54  # rolou até a altura capturada, não até 60000


def test_main_avisa_pagina_truncada(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(capturar, "capturar", lambda u, s: {
        "url": u, "titulo": "T", "precos": [], "links_checkout": [], "garantia": "",
        "truncada": True, "altura_capturada": 48000})
    assert capturar.main(["--url", "https://x.com", "--saida", str(tmp_path)]) == 0
    assert "Página muito longa: capturei só os primeiros 48000 px." in capsys.readouterr().out


def test_limpar_preserva_pagina_foo(tmp_path):
    for n in ("pagina-01.png", "pagina-foo.png", "pagina-1.png"):
        (tmp_path / n).write_text("x")
    capturar._limpar(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["pagina-1.png", "pagina-foo.png"]


def test_capturar_sem_meta_viewport_usa_largura_real(tmp_path):
    pytest.importorskip("playwright")
    html = tmp_path / "lp.html"
    html.write_text('<html><body style="margin:0"><div style="width:980px;height:3000px;background:#ccc">x</div>'
                    "</body></html>", encoding="utf-8")
    try:
        dados = capturar.capturar(html.as_uri(), tmp_path / "out")
    except Exception as e:
        if isinstance(e, ImportError) or "Executable doesn't exist" in str(e):
            pytest.skip(f"Chromium do Playwright indisponível: {e}")
        raise
    assert dados["largura"] == 980
    largura_png = int.from_bytes((tmp_path / "out" / dados["prints"][0]).read_bytes()[16:20], "big")
    assert largura_png == 980


def test_capturar_nao_repete_em_erro_de_dns(tmp_path, monkeypatch):
    log = {"goto": [], "shots": []}
    _fake_playwright(monkeypatch, log, erro=RuntimeError("net::ERR_NAME_NOT_RESOLVED"))
    with pytest.raises(RuntimeError):
        capturar.capturar("https://nao.invalid", tmp_path / "o")
    assert len(log["goto"]) == 1


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
    except Exception as e:
        if isinstance(e, ImportError) or "Executable doesn't exist" in str(e):
            pytest.skip(f"Chromium do Playwright indisponível: {e}")
        raise
    out = tmp_path / "out"
    assert dados["titulo"] == "Oferta Teste"
    assert dados["precos"] == ["R$ 37,00"]
    assert dados["links_checkout"] == ["https://pay.kiwify.com.br/ZZ"]
    assert "Método X" in (out / "pagina.txt").read_text()
    assert (out / "dobra.png").stat().st_size > 0
    assert len(dados["prints"]) >= 2 and dados["altura"] > 2400
    for nome in dados["prints"]:
        assert (out / nome).stat().st_size > 0
    salvo = json.loads((out / "dados.json").read_text())
    assert salvo["garantia"] == "garantia de 30 dias" and salvo["prints"] == dados["prints"]
    assert salvo["url_final"].startswith("file://")
