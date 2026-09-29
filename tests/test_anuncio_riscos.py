import json

import pytest

import anuncio_riscos as ar


def _a(**kw):
    base = {"id": "a", "formato": "estatico", "headline_imagem": "Comida pronta", "texto_principal": "",
            "titulo": "", "descricao": ""}
    base.update(kw)
    return base


@pytest.mark.parametrize("campo,texto,trecho", [
    ("texto_principal", "Você está acima do peso e cansada?", "atributo pessoal"),
    ("texto_principal", "Veja o antes e depois da Ana", "antes e depois"),
    ("titulo", "Ganhe até R$ 5.000 por mês", "ganho"),
    ("texto_principal", "Resultado garantido ou seu dinheiro", "garantido"),
    ("texto_principal", "Perca 5 kg em 21 dias", "prazo"),
    ("texto_principal", "Método que cura a ansiedade", "saúde"),
    ("texto_principal", "Para mulheres acima de 40 anos", "idade"),
    ("titulo", "Últimas vagas, clique aqui", "clique"),
    ("headline_imagem", "uma duas três quatro cinco seis sete oito nove dez onze doze treze", "texto demais"),
])
def test_avisa(campo, texto, trecho):
    avisos = ar.avaliar(_a(**{campo: texto}))
    assert any(trecho in a.lower() for a in avisos), avisos


def test_video_avalia_hooks_e_corpo():
    v = {"id": "v", "formato": "video", "hooks": ["Você está endividado?"], "corpo": "ok", "cta_falado": "ok",
         "texto_principal": "", "titulo": "", "descricao": ""}
    assert ar.avaliar(v)


@pytest.mark.parametrize("texto", [
    "Garantia de satisfação de 7 dias", "Comida pronta pra 15 dias sem cozinhar", "Receitas testadas passo a passo",
])
def test_nao_avisa_texto_neutro(texto):
    assert ar.avaliar(_a(texto_principal=texto)) == []


def test_main_imprime_e_sai_0(tmp_path, capsys):
    (tmp_path / "anuncios.json").write_text(json.dumps({"anuncios": [
        {"id": "a", "angulo": "x", "formato": "estatico", "headline_imagem": "Antes e depois",
         "texto_principal": "t", "titulo": "t"},
        {"id": "b", "angulo": "x", "formato": "estatico", "headline_imagem": "Ok", "texto_principal": "t", "titulo": "t"}]}))
    assert ar.main(["--pasta", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "a:" in out and "antes e depois" in out.lower() and "b: nenhum aviso" in out.lower()
    assert ar.main(["--pasta", str(tmp_path / "nada")]) == 1
    assert ar.main([]) == 1


@pytest.mark.parametrize("texto", [
    "Perca 5kg em 21 dias", "Perca 5 kg em 21 dias", "Você está com sobrepeso?", "Você tem diabetes?",
    "Você sofre de diabetes há anos", "Cure a ansiedade", "dinheiro garantido", "Voce e gordo", "Voce esta acima do peso",
    "Mulheres acima dos 40 anos", "Faturei 30 mil por mês",
])
def test_recall(texto):
    assert ar.avaliar(_a(texto_principal=texto)), texto


@pytest.mark.parametrize("texto", [
    "Aprenda a cozinhar em 7 dias", "Ganhe tempo", "Ganhe 10% de desconto", "Você tem filhos pequenos?",
    "Renda extra", "A cura para o tédio", "Você é capaz", "Antes de começar, depois de comprar",
    "cardápio garantido", "Perca o medo em 4 semanas", "Mulheres com mais de 40 anos de experiência",
    "Elimine a bagunça em 3 dias", "Tudo garantido: entrega rápida",
    "Você é capaz de cozinhar em 20 minutos com estas receitas.",
    "Renda extra: o guia mostra 10 ideias e custa R$ 47.",
])
def test_sem_falso_positivo(texto):
    assert ar.avaliar(_a(texto_principal=texto)) == [], texto


def test_argparse_em_portugues(capsys):
    assert ar.main([]) == 1
    err = capsys.readouterr().err
    assert "falta --pasta" in err and "required" not in err
    assert ar.main(["--xyz"]) == 1
    assert "the " not in capsys.readouterr().err


def test_ctrl_c(monkeypatch, capsys):
    def boom(_):
        raise KeyboardInterrupt
    monkeypatch.setattr(ar, "ler_anuncios", boom)
    assert ar.main(["--pasta", "x"]) == 130
    assert "Cancelado." in capsys.readouterr().err
