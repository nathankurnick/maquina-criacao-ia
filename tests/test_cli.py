from nucleo import chaves, cli


def test_versao(ambiente, capsys):
    (ambiente / "home").mkdir()
    (ambiente / "home" / "VERSION").write_text("9.9.9\n")
    assert cli.main(["versao"]) == 0
    assert capsys.readouterr().out.strip() == "9.9.9"


def test_projeto_novo_listar_caminho(ambiente, capsys):
    assert cli.main(["projeto", "novo", "Meu Produto"]) == 0
    assert cli.main(["projeto", "listar"]) == 0
    assert cli.main(["projeto", "caminho", "meu-produto"]) == 0
    out = capsys.readouterr().out
    assert "meu-produto" in out
    assert str(ambiente / "projetos" / "meu-produto") in out


def test_projeto_inexistente_mensagem_amigavel(ambiente, capsys):
    assert cli.main(["projeto", "caminho", "nada"]) == 1
    err = capsys.readouterr().err
    assert "não existe" in err and "Traceback" not in err


def test_oferta_faltando(ambiente, capsys):
    cli.main(["projeto", "novo", "X"])
    capsys.readouterr()
    assert cli.main(["oferta", "faltando", "x"]) == 0
    assert capsys.readouterr().out.split() == ["nome", "nicho", "avatar", "promessa", "mecanismo", "preco"]


def test_status_mostra_chaves(ambiente, capsys):
    chaves.salvar_chave("KIE_API_KEY", "x")
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "✅ KIE" in out and "— Netlify" in out


def test_configurar_chaves_pula_e_tenta_de_novo(ambiente, monkeypatch):
    respostas = iter(["ruim", "boa", ""])  # KIE: ruim, depois boa. Netlify: pula.
    monkeypatch.setattr(cli, "testar_chave",
                        lambda n, v: (_ for _ in ()).throw(cli.MaquinaErro("recusada")) if v == "ruim" else "ok")
    saida = []
    cli.configurar_chaves(perguntar=lambda _: next(respostas), imprimir=saida.append)
    assert chaves.ler_chaves() == {"KIE_API_KEY": "boa"}
    assert any("recusada" in s for s in saida)


def test_erro_inesperado_vai_pro_log(ambiente, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_projeto", lambda a: 1 / 0)
    assert cli.main(["projeto", "listar"]) == 1
    err = capsys.readouterr().err
    assert "Algo deu errado" in err and "Traceback" not in err
    assert "ZeroDivisionError" in (ambiente / "home" / "log" / "maquina.log").read_text()
