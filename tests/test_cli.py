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


def test_configurar_chaves_formato_ruim_nao_chama_rede_e_conta_tentativa(ambiente, monkeypatch):
    chamadas = []
    monkeypatch.setattr(cli, "testar_chave", lambda n, v: chamadas.append(v) or "ok")
    respostas = iter(["com espaco", "a​b", "tambem ruim", "", ])
    saida = []
    cli.configurar_chaves(perguntar=lambda _: next(respostas, ""), imprimir=saida.append)
    assert chamadas == []
    assert sum("caracteres estranhos" in s for s in saida) == 3
    assert chaves.ler_chaves() == {}


def test_argparse_erro_em_portugues(ambiente, capsys):
    import pytest
    with pytest.raises(SystemExit) as e:
        cli.main(["comando-que-nao-existe"])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert "Comando inválido" in err and "maquina --help" in err
    assert "usage:" not in err


def _oferta_definir(*campos, slug="p"):
    return cli.main(["oferta", "definir", slug, *campos])


def test_oferta_definir_cria_arquivo_e_divide_no_primeiro_igual(ambiente, capsys):
    from nucleo.projeto import abrir_projeto, criar_projeto, ler_oferta
    criar_projeto("p")
    assert _oferta_definir("nome=Barriga Leve", "promessa=Perca 5kg: em 21 dias=ou menos",
                           "paleta=#1a2b3c", "preco=47.90") == 0
    o = ler_oferta(abrir_projeto("p"))
    assert (o.nome, o.promessa, o.paleta, o.preco) == (
        "Barriga Leve", "Perca 5kg: em 21 dias=ou menos", "#1a2b3c", "47.90")


def test_oferta_definir_preserva_corpo_e_listas(ambiente):
    from nucleo.projeto import Oferta, abrir_projeto, criar_projeto, ler_oferta, salvar_oferta
    pasta = criar_projeto("p")
    salvar_oferta(pasta, Oferta(nome="A", bonus=["b1"], entregaveis=["e1", "e2"], corpo="texto livre"))
    assert _oferta_definir("nicho=saúde") == 0
    o = ler_oferta(pasta)
    assert (o.nome, o.nicho, o.bonus, o.entregaveis, o.corpo) == ("A", "saúde", ["b1"], ["e1", "e2"], "texto livre")


def test_oferta_definir_campo_desconhecido_ou_lista(ambiente, capsys):
    from nucleo.projeto import criar_projeto
    criar_projeto("p")
    for campo in ("foo=1", "bonus=x", "entregaveis=y", "corpo=z", "semigual"):
        assert _oferta_definir(campo) == 1
    err = capsys.readouterr().err
    assert err.count("❌") == 5 and "Traceback" not in err
    assert "maquina oferta adicionar" in err


def test_oferta_definir_projeto_invalido(ambiente, capsys):
    assert _oferta_definir("nome=x", slug="../x") == 1
    assert "inválido" in capsys.readouterr().err


def test_oferta_adicionar_sem_duplicar(ambiente):
    from nucleo.projeto import abrir_projeto, criar_projeto, ler_oferta
    criar_projeto("p")
    for item in ("Guia", "Planilha", "Guia"):
        assert cli.main(["oferta", "adicionar", "p", "entregaveis", item]) == 0
    assert cli.main(["oferta", "adicionar", "p", "bonus", "Extra"]) == 0
    o = ler_oferta(abrir_projeto("p"))
    assert o.entregaveis == ["Guia", "Planilha"] and o.bonus == ["Extra"]


def test_oferta_adicionar_lista_invalida(ambiente, capsys):
    from nucleo.projeto import criar_projeto
    criar_projeto("p")
    assert cli.main(["oferta", "adicionar", "p", "nome", "x"]) == 1
    assert "entregaveis" in capsys.readouterr().err


def test_oferta_mostrar_json(ambiente, capsys):
    import json
    from nucleo.projeto import Oferta, criar_projeto, salvar_oferta
    pasta = criar_projeto("p")
    salvar_oferta(pasta, Oferta(nome="A", bonus=["b"], corpo="livre"))
    assert cli.main(["oferta", "mostrar", "p"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["nome"] == "A" and d["bonus"] == ["b"] and d["corpo"] == "livre" and d["preco"] == ""
    assert len(d) == 12


def test_oferta_mostrar_sem_arquivo_vazio(ambiente, capsys):
    import json
    from nucleo.projeto import criar_projeto
    criar_projeto("p")
    assert cli.main(["oferta", "mostrar", "p"]) == 0
    assert json.loads(capsys.readouterr().out)["nome"] == ""


def test_status_json(ambiente, capsys, monkeypatch):
    import json
    from nucleo.projeto import criar_projeto
    criar_projeto("p")
    chaves.salvar_chave("KIE_API_KEY", "k")
    assert cli.main(["status", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["chaves"] == {"KIE_API_KEY": True, "NETLIFY_TOKEN": False}
    assert d["projetos"] == ["p"] and "versao" in d


def test_atualizar_mostra_versao_e_passos(ambiente, capsys):
    (ambiente / "home").mkdir()
    (ambiente / "home" / "VERSION").write_text("1.2.3\n")
    assert cli.main(["atualizar"]) == 0
    out = capsys.readouterr().out
    assert "1.2.3" in out and "área de membros" in out and "Instalar Máquina.command" in out
    assert "chaves" in out and "projetos" in out
