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
