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


def test_ctrl_c_cancela_sem_traceback(ambiente, monkeypatch, capsys):
    def _boom(a):
        raise KeyboardInterrupt
    monkeypatch.setattr(cli, "_projeto", _boom)
    assert cli.main(["projeto", "listar"]) == 130
    err = capsys.readouterr().err
    assert "Cancelado." in err and "Traceback" not in err


def test_chaves_eof_mensagem_amigavel(ambiente, monkeypatch, capsys):
    def _eof(_):
        raise EOFError
    monkeypatch.setattr(cli.configurar_chaves, "__defaults__", (_eof, print))
    assert cli.main(["chaves"]) == 1
    err = capsys.readouterr().err
    assert "terminal" in err.lower() and "suporte" not in err and "Traceback" not in err
    assert not (ambiente / "home" / "log" / "maquina.log").exists()


def test_configurar_chaves_eof_vira_maquina_erro(ambiente):
    def _eof(_):
        raise EOFError
    import pytest
    with pytest.raises(cli.MaquinaErro):
        cli.configurar_chaves(perguntar=_eof, imprimir=lambda s: None)


def test_projeto_novo_e_caminho_sem_valor(ambiente, capsys):
    assert cli.main(["projeto", "novo"]) == 1
    assert "Faltou o nome do projeto." in capsys.readouterr().err
    assert cli.main(["projeto", "caminho"]) == 1
    assert "Faltou o nome (slug) do projeto" in capsys.readouterr().err
