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
    monkeypatch.setattr(ec, "baixar", lambda url, destino: destino.write_bytes(b"png") or destino)
    destino = ec.gerar_arte(tmp_path, "pão rústico sobre mesa de madeira", "k")
    assert destino == tmp_path / "arte.png" and destino.read_bytes() == b"png"
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
