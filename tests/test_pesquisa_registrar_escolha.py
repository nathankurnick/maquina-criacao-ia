import json

import registrar_escolha as re_


def _busca(tmp_path):
    b = tmp_path / "proj" / "pesquisa" / "2026-09-28-x"
    b.mkdir(parents=True)
    (b / "ofertas.json").write_text(json.dumps({"ofertas": [{"chave": "a.com"}, {"chave": "whatsapp:Página Ágil"}]}))
    return b


def test_grava_escolhida_json_em_pesquisa(tmp_path):
    b = _busca(tmp_path)
    o = b.parent / "oferta-whatsapp-pagina-agil"
    assert re_.main(["--busca", str(b), "--oferta", "2", "--pasta-oferta", str(o)]) == 0
    d = json.loads((b.parent / "escolhida.json").read_text())
    assert d["busca"] == str(b) and d["oferta"] == 2 and d["chave"] == "whatsapp:Página Ágil"
    assert d["pasta_oferta"] == str(o) and d["data"]


def test_sobrescreve(tmp_path):
    b = _busca(tmp_path)
    re_.main(["--busca", str(b), "--oferta", "1", "--pasta-oferta", "x"])
    re_.main(["--busca", str(b), "--oferta", "2", "--pasta-oferta", "y"])
    assert json.loads((b.parent / "escolhida.json").read_text())["oferta"] == 2


def test_erros_amigaveis(tmp_path, capsys):
    b = _busca(tmp_path)
    assert re_.main(["--busca", str(b), "--oferta", "7", "--pasta-oferta", "x"]) == 1
    assert re_.main(["--busca", str(tmp_path / "nada"), "--oferta", "1", "--pasta-oferta", "x"]) == 1
    assert re_.main([]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_erro_ao_gravar_vai_pro_log(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("MAQUINA_HOME", str(home))
    b = _busca(tmp_path)
    (b.parent / "escolhida.json").mkdir()  # gravar em cima de uma pasta dá OSError
    assert re_.main(["--busca", str(b), "--oferta", "1", "--pasta-oferta", "x"]) == 1
    assert "Traceback" not in capsys.readouterr().err
    assert "Traceback" in (home / "log" / "maquina.log").read_text()
