import json

import pytest

import entregavel_capa as ec


def _pasta(tmp_path):
    p = tmp_path / "entregaveis" / "guia"
    p.mkdir(parents=True)
    (p / "meta.json").write_text(json.dumps({"titulo": "Guia <do> Pão", "subtitulo": "Do zero",
                                             "tipo": "guia", "autor": "Ana"}))
    return p


def test_html_capa_com_e_sem_arte():
    meta = {"titulo": "Guia <do> Pão", "subtitulo": "S", "tipo": "guia", "autor": "Ana"}
    sem = ec.html_capa(meta, "preto-dourado")
    assert "Guia &lt;do&gt; Pão" in sem and "--pg-destaque:#d4af37" in sem and 'class="arte"' not in sem
    com = ec.html_capa(meta, "preto-dourado", arte="arte.png")
    assert '<img class="arte" src="arte.png" alt="">' in com and 'class="veu"' in com
    assert "Guia prático" in com


def test_html_mockup_usa_a_capa():
    h = ec.html_mockup("capa.png", "azul-laranja")
    assert "url('capa.png')" in h and 'class="livro"' in h


def test_gerar_arte_chama_kie_e_baixa(tmp_path, monkeypatch):
    chamadas = {}
    monkeypatch.setattr(ec, "criar_tarefa", lambda chave, modelo, entrada: chamadas.update(
        chave=chave, modelo=modelo, entrada=entrada) or "t1")
    monkeypatch.setattr(ec, "aguardar", lambda chave, tid, intervalo=6, limite=300: {"resultUrls": ["https://u/a.png"]})
    monkeypatch.setattr(ec, "baixar", lambda url, destino: destino.write_bytes(b"\x89PNG\r\n\x1a\nx") or destino)
    destino = ec.gerar_arte(tmp_path, "pão rústico sobre mesa de madeira", "k")
    assert destino == tmp_path / "arte.png" and destino.read_bytes().startswith(b"\x89PNG")
    assert chamadas["modelo"] == "nano-banana-2"
    assert chamadas["entrada"] == {"prompt": "pão rústico sobre mesa de madeira", "aspect_ratio": "2:3",
                                   "output_format": "png"}


def test_main_arte_sem_chave_imprime_prompt_e_segue(ambiente, tmp_path, monkeypatch, capsys):
    p = _pasta(tmp_path)
    monkeypatch.setattr(ec, "gerar_capa", lambda pasta, paleta: {"capa": pasta / "capa.png", "mockup": pasta / "mockup.png"})
    assert ec.main(["--pasta", str(p), "--arte", "mesa com pães"]) == 0
    out = capsys.readouterr().out
    assert "mesa com pães" in out and "arte.png" in out


def test_main_kie_falha_avisa_e_segue(ambiente, tmp_path, monkeypatch, capsys):
    p = _pasta(tmp_path)
    monkeypatch.setenv("KIE_API_KEY", "k")

    def quebra(pasta, prompt, chave):
        raise ec.KieErro("Seus créditos da KIE acabaram.")

    monkeypatch.setattr(ec, "gerar_arte", quebra)
    monkeypatch.setattr(ec, "gerar_capa", lambda pasta, paleta: {"capa": pasta / "capa.png", "mockup": pasta / "mockup.png"})
    assert ec.main(["--pasta", str(p), "--arte", "x"]) == 0
    assert "créditos" in capsys.readouterr().out


def test_gerar_capa_de_verdade(tmp_path):
    pytest.importorskip("playwright")
    p = _pasta(tmp_path)
    try:
        r = ec.gerar_capa(p, "verde-branco")
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise
    capa, mockup = r["capa"].read_bytes(), r["mockup"].read_bytes()
    assert capa[:8] == b"\x89PNG\r\n\x1a\n" and mockup[:8] == b"\x89PNG\r\n\x1a\n"
    assert int.from_bytes(capa[16:20], "big") == 1240 and int.from_bytes(capa[20:24], "big") == 1754
    assert int.from_bytes(mockup[16:20], "big") == 1200


def test_main_erros(tmp_path, capsys):
    assert ec.main(["--pasta", str(tmp_path / "nada")]) == 1
    assert "meta.json" in capsys.readouterr().err
    assert ec.main([]) == 1


def test_titulo_longo_reduz_a_fonte():
    curto = ec.html_capa({"titulo": "Pão", "tipo": "guia"}, "azul-laranja")
    longo = ec.html_capa({"titulo": "x" * 70, "tipo": "guia"}, "azul-laranja")
    enorme = ec.html_capa({"titulo": "x" * 120, "tipo": "guia"}, "azul-laranja")
    assert "<h1>" in curto and '<h1 class="longo">' in longo and '<h1 class="enorme">' in enorme


def test_gerar_capa_nao_deixa_temporarios(tmp_path):
    pytest.importorskip("playwright")
    p = _pasta(tmp_path)
    try:
        ec.gerar_capa(p, "azul-laranja")
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise
    assert sorted(x.name for x in p.iterdir()) == ["capa.png", "meta.json", "mockup.png"]


PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


def _kie_ok(monkeypatch, conteudo):
    monkeypatch.setattr(ec, "criar_tarefa", lambda *a, **k: "t1")
    monkeypatch.setattr(ec, "aguardar", lambda chave, tid, intervalo=6, limite=300: {"resultUrls": ["https://u/a.png"]})
    monkeypatch.setattr(ec, "baixar", lambda url, destino: destino.write_bytes(conteudo) or destino)


def test_gerar_arte_orcamento_de_tempo(tmp_path, monkeypatch):
    vistos = {}
    monkeypatch.setattr(ec, "criar_tarefa", lambda *a, **k: "t1")
    monkeypatch.setattr(ec, "aguardar", lambda chave, tid, intervalo=0, limite=0: vistos.update(i=intervalo, l=limite) or {"resultUrls": ["u"]})
    monkeypatch.setattr(ec, "baixar", lambda url, destino: destino.write_bytes(PNG))
    ec.gerar_arte(tmp_path, "x", "k")
    assert vistos == {"i": 5, "l": 150}


@pytest.mark.parametrize("conteudo,ok", [(PNG, True), (b"\xff\xd8\xff\xe0abc", True),
                                         (b"RIFF\x00\x00\x00\x00WEBPVP8 ", True), (b"<html>erro</html>", False)])
def test_gerar_arte_valida_o_arquivo(tmp_path, monkeypatch, conteudo, ok):
    _kie_ok(monkeypatch, conteudo)
    (tmp_path / "arte.png").write_bytes(b"antiga")
    if ok:
        assert ec.gerar_arte(tmp_path, "x", "k").read_bytes() == conteudo
    else:
        with pytest.raises(ec.KieErro, match="não é imagem"):
            ec.gerar_arte(tmp_path, "x", "k")
        assert (tmp_path / "arte.png").read_bytes() == b"antiga"
        assert not (tmp_path / ".arte.tmp.png").exists()


def test_main_erro_inesperado_na_arte_nao_aborta(ambiente, tmp_path, monkeypatch, capsys):
    p = _pasta(tmp_path)
    monkeypatch.setenv("KIE_API_KEY", "k")
    monkeypatch.setattr(ec, "gerar_arte", lambda *a: (_ for _ in ()).throw(OSError("disco")))
    monkeypatch.setattr(ec, "gerar_capa", lambda pasta, paleta: {"capa": pasta / "capa.png", "mockup": pasta / "mockup.png"})
    assert ec.main(["--pasta", str(p), "--arte", "x"]) == 0
    out = capsys.readouterr().out
    assert "erro inesperado" in out and "fundo na cor da paleta" in out


def test_main_arte_antiga_e_reaproveitada(ambiente, tmp_path, monkeypatch, capsys):
    p = _pasta(tmp_path)
    (p / "arte.png").write_bytes(PNG)
    monkeypatch.setattr(ec, "gerar_capa", lambda pasta, paleta: {"capa": pasta / "capa.png", "mockup": pasta / "mockup.png"})
    assert ec.main(["--pasta", str(p), "--arte", "x"]) == 0  # sem chave
    out = capsys.readouterr().out
    assert "Usei a arte que já estava na pasta (arte.png)" in out and "fundo na cor da paleta" not in out
    monkeypatch.setenv("KIE_API_KEY", "k")
    monkeypatch.setattr(ec, "gerar_arte", lambda *a: (_ for _ in ()).throw(ec.KieErro("fila cheia")))
    assert ec.main(["--pasta", str(p), "--arte", "x"]) == 0
    out = capsys.readouterr().out
    assert "Usei a arte que já estava" in out and "fundo na cor da paleta" not in out


def test_main_distingue_erro_permanente(ambiente, tmp_path, monkeypatch, capsys):
    p = _pasta(tmp_path)
    monkeypatch.setenv("KIE_API_KEY", "k")
    monkeypatch.setattr(ec, "gerar_capa", lambda pasta, paleta: {"capa": pasta / "capa.png", "mockup": pasta / "mockup.png"})
    monkeypatch.setattr(ec, "gerar_arte", lambda *a: (_ for _ in ()).throw(ec.KieErroPermanente("chave ruim")))
    ec.main(["--pasta", str(p), "--arte", "x"])
    assert "repetir não adianta: chave ruim" in capsys.readouterr().out
    monkeypatch.setattr(ec, "gerar_arte", lambda *a: (_ for _ in ()).throw(ec.KieErro("fila")))
    ec.main(["--pasta", str(p), "--arte", "x"])
    assert "tente de novo mais tarde: fila" in capsys.readouterr().out


def test_gerar_capa_falha_mantem_capa_antiga(tmp_path, monkeypatch):
    sync = pytest.importorskip("playwright.sync_api")
    p = _pasta(tmp_path)
    (p / "capa.png").write_bytes(b"velha")
    (p / "mockup.png").write_bytes(b"velho")
    from playwright.sync_api import Page

    def quebra(self, *a, **k):
        raise RuntimeError("screenshot falhou")

    monkeypatch.setattr(Page, "screenshot", quebra)
    with pytest.raises(RuntimeError):
        ec.gerar_capa(p, "azul-laranja")
    assert (p / "capa.png").read_bytes() == b"velha" and (p / "mockup.png").read_bytes() == b"velho"
    assert sorted(x.name for x in p.iterdir()) == ["capa.png", "meta.json", "mockup.png"]
