import json
import stat

import pytest

import pagina_conteudo as pc


def _completo():
    return {
        "hero": {"badge": "B", "headline": "Aprenda **pão**", "subheadline": "S", "cta": "QUERO"},
        "carrossel": {"titulo": "Por dentro", "descricao": "D"},
        "paraQuem": {"titulo": "T", "itens": [{"titulo": "A", "descricao": "a"}]},
        "conteudo": {"titulo": "T", "itens": [{"icone": "livro", "titulo": "C1", "descricao": "c"},
                                              {"icone": "nao-existe", "titulo": "C2", "descricao": "c"}]},
        "incluso": {"titulo": "T", "itens": [{"titulo": "I", "descricao": "i"}]},
        "entrega": {"titulo": "T", "itens": [{"titulo": "E", "descricao": "e"}]},
        "bonus": {"titulo": "T", "itens": [{"titulo": "Bx", "descricao": "b", "valor": "R$47"}]},
        "depoimentos": {"titulo": "Veja"},
        "planos": {"titulo": "P", "basico": {"nome": "BÁSICO", "itens": ["x"], "precoPor": "R$ 27",
                                              "checkoutUrl": "https://pay.kiwify.com.br/a"}},
        "garantia": {"dias": 7, "texto": "Devolvemos."},
        "faq": {"itens": [{"pergunta": "P?", "resposta": "R."}]},
        "rodape": {"nomeProduto": "Pão Fácil"},
    }


def test_paletas_e_icones():
    assert set(pc.PALETAS) == {"azul-laranja", "preto-dourado", "verde-branco", "vermelho-preto", "grafite-ciano"}
    assert pc.PALETAS["azul-laranja"] == {
        "fundo": "#0a1628", "fundo-claro": "#eef3fb", "fundo-medio": "#0f3460", "destaque": "#f59e0b",
        "cta": "#f59e0b", "cta-texto": "#0a1628", "texto-claro": "#ffffff", "texto-escuro": "#0a1628"}
    assert len(pc.ICONES) == 12 and "estrela" in pc.ICONES
    assert set(pc.PALETAS_ROTULO) == set(pc.PALETAS)


def test_normalizar_completo_ativa_tudo_por_padrao():
    c, avisos = pc.normalizar(_completo())
    assert all(c[b]["ativo"] for b in ("hero", "paraQuem", "conteudo", "incluso", "entrega",
                                       "bonus", "planos", "garantia", "faq", "rodape"))
    assert c["conteudo"]["itens"][1]["icone"] == "estrela"
    assert c["planos"]["basico"]["ativo"] is True
    assert c["planos"]["premium"]["ativo"] is False
    assert c["planos"]["basico"]["cta"] == "QUERO ACESSAR AGORA"
    assert c["rodape"]["disclaimer"] == pc.DISCLAIMER_PADRAO
    assert c["garantia"]["titulo"] == "GARANTIA INCONDICIONAL"
    assert avisos == []


def test_normalizar_vazio_desativa_e_explica():
    c, avisos = pc.normalizar({})
    assert not c["hero"]["ativo"] and not c["planos"]["ativo"] and not c["faq"]["ativo"]
    assert c["rodape"]["ativo"] is True
    texto = " ".join(avisos)
    assert "headline" in texto and "checkout" in texto


def test_texto_vazio_cai_no_padrao_e_ativo_false_respeitado():
    bruto = _completo()
    bruto["hero"]["cta"] = "   "
    bruto["faq"]["ativo"] = False
    c, _ = pc.normalizar(bruto)
    assert c["hero"]["cta"] == "QUERO ACESSAR AGORA"
    assert c["faq"]["ativo"] is False


def test_premium_com_mesmo_checkout_e_desativado_com_aviso():
    bruto = _completo()
    bruto["planos"]["premium"] = {"ativo": True, "checkoutUrl": "https://pay.kiwify.com.br/a", "precoPor": "R$ 97"}
    c, avisos = pc.normalizar(bruto)
    assert c["planos"]["premium"]["ativo"] is False
    assert any("mesmo checkout" in a for a in avisos)


def test_disclaimer_curto_vira_padrao_e_dias_invalido_vira_7():
    bruto = _completo()
    bruto["rodape"]["disclaimer"] = "curto"
    bruto["garantia"]["dias"] = "sete"
    c, _ = pc.normalizar(bruto)
    assert c["rodape"]["disclaimer"] == pc.DISCLAIMER_PADRAO
    assert c["garantia"]["dias"] == 7


def test_normalizar_tolera_lixo():
    c, _ = pc.normalizar({"hero": "x", "conteudo": {"itens": [None, 5, {"titulo": 3}]}, "planos": []})
    assert c["conteudo"]["itens"] == [] and not c["conteudo"]["ativo"]
    c2, _ = pc.normalizar(["não é objeto"])
    assert c2["rodape"]["ativo"] is True


def test_config_padrao_ler_salvar(tmp_path):
    assert pc.ler_config(tmp_path) == pc.CONFIG_PADRAO
    cfg = dict(pc.CONFIG_PADRAO, paleta="preto-dourado", site_id="abc")
    arq = pc.salvar_config(tmp_path, cfg)
    assert arq == tmp_path / "config.json"
    assert pc.ler_config(tmp_path)["site_id"] == "abc"
    (tmp_path / "config.json").write_text('{"paleta": "inexistente", "extra": 1}')
    lido = pc.ler_config(tmp_path)
    assert lido["paleta"] == pc.PALETA_PADRAO and "extra" not in lido


def test_config_json_quebrado_da_erro_amigavel(tmp_path):
    (tmp_path / "config.json").write_text("{quebrado")
    with pytest.raises(ValueError, match="config.json"):
        pc.ler_config(tmp_path)


@pytest.mark.parametrize("chave,valor,esperado", [
    ("paleta", "verde-branco", "verde-branco"),
    ("pixel_meta", " 123456789012345 ", "123456789012345"),
    ("pixel_meta", "", ""),
    ("pixel_google", "G-ABC123XYZ", "G-ABC123XYZ"),
    ("seo_titulo", "Título", "Título"),
])
def test_validar_valor_ok(chave, valor, esperado):
    assert pc.validar_valor(chave, valor) == esperado


@pytest.mark.parametrize("chave,valor", [
    ("paleta", "rosa"), ("pixel_meta", "abc"), ("pixel_google", "123"), ("site_id", "x"), ("nada", "x"),
])
def test_validar_valor_recusa(chave, valor):
    with pytest.raises(ValueError):
        pc.validar_valor(chave, valor)
