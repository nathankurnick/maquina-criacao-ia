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


def test_icone_lista_ou_dict_cai_no_padrao():
    bruto = _completo()
    bruto["conteudo"]["itens"] = [{"icone": ["x"], "titulo": "A"}, {"icone": {"a": 1}, "titulo": "B"}]
    c, _ = pc.normalizar(bruto)
    assert [i["icone"] for i in c["conteudo"]["itens"]] == ["estrela", "estrela"]


def test_dias_string_numerica_e_invalido_com_aviso():
    for bruto_dias, esperado in (("10", 10), (" 30 ", 30)):
        bruto = _completo()
        bruto["garantia"]["dias"] = bruto_dias
        c, avisos = pc.normalizar(bruto)
        assert c["garantia"]["dias"] == esperado and avisos == []
    bruto = _completo()
    bruto["garantia"]["dias"] = "sete"
    c, avisos = pc.normalizar(bruto)
    assert c["garantia"]["dias"] == 7
    assert "garantia: dias inválido — usei 7." in avisos


def test_preco_numerico_vira_texto():
    bruto = _completo()
    bruto["planos"]["basico"]["precoPor"] = 97
    bruto["planos"]["basico"]["precoDe"] = 197.5
    bruto["bonus"]["itens"][0]["valor"] = 47
    c, _ = pc.normalizar(bruto)
    assert c["planos"]["basico"]["precoPor"] == "97"
    assert c["planos"]["basico"]["precoDe"] == "197.5"
    assert c["bonus"]["itens"][0]["valor"] == "47"


def test_salvar_config_permissao_644(tmp_path):
    arq = pc.salvar_config(tmp_path, dict(pc.CONFIG_PADRAO))
    assert stat.S_IMODE(arq.stat().st_mode) == 0o644


@pytest.mark.parametrize("valor", [None, 5, ["a"]])
def test_validar_valor_nao_texto(valor):
    with pytest.raises(ValueError, match="texto"):
        pc.validar_valor("paleta", valor)


def test_url_segura_rejeita_barra_invertida_apos_barra():
    assert not pc.url_segura("/\\evil.com")
    assert not pc.url_segura("//evil.com")
    assert pc.url_segura("/obrigado")


@pytest.mark.parametrize("ruim", ["#", "/x", "http://pay.x.com/a", "https://pay.kiwify.com.br/SEU-LINK",
                                  "https://pay.kiwify.com.br/seu-link", "https:///x", "https://semponto"])
def test_checkout_estrito_desliga_plano_com_aviso(ruim):
    bruto = _completo()
    bruto["planos"]["basico"]["checkoutUrl"] = ruim
    c, avisos = pc.normalizar(bruto)
    assert c["planos"]["basico"]["checkoutUrl"] == "" and not c["planos"]["basico"]["ativo"]
    assert any("endereço real de pagamento" in a and "https://pay.kiwify.com.br/" in a for a in avisos)


def test_checkout_https_real_passa():
    c, avisos = pc.normalizar(_completo())
    assert c["planos"]["basico"]["ativo"] and not any("endereço real" in a for a in avisos)


def test_disclaimer_hifen_significa_sem_aviso():
    bruto = _completo()
    bruto["rodape"]["disclaimer"] = "-"
    c, _ = pc.normalizar(bruto)
    assert c["rodape"]["disclaimer"] == ""


def test_url_editavel_no_config_so_https():
    assert pc.validar_valor("url", " https://x.netlify.app ") == "https://x.netlify.app"
    for ruim in ("http://x.com", "x.com", "javascript:alert(1)"):
        with pytest.raises(ValueError):
            pc.validar_valor("url", ruim)
    with pytest.raises(ValueError):
        pc.validar_valor("site_id", "abc")


def test_entregavel_no_hero_e_nos_bonus():
    bruto = {"hero": {"headline": "H", "entregavel": "pack-casas"},
             "bonus": {"itens": [{"titulo": "A", "entregavel": "guia-terreno"}, {"titulo": "B"},
                                 {"titulo": "C", "entregavel": "../fora"}]}}
    c, _ = pc.normalizar(bruto)
    assert c["hero"]["entregavel"] == "pack-casas"
    assert [i["entregavel"] for i in c["bonus"]["itens"]] == ["guia-terreno", "", ""]


def test_entregavel_malformado_avisa():
    bruto = {"hero": {"headline": "H", "entregavel": "Guia Marmitas"},
             "bonus": {"itens": [{"titulo": "A"}, {"titulo": "B", "entregavel": "../fora"}]}}
    c, avisos = pc.normalizar(bruto)
    assert c["hero"]["entregavel"] == ""
    assert any(a.startswith('hero: "entregavel" inválido ("Guia Marmitas")') for a in avisos)
    assert any(a.startswith('bonus #2: "entregavel" inválido') for a in avisos)
    _, ok = pc.normalizar({"hero": {"headline": "H", "entregavel": "guia-marmitas"}})
    assert not any("entregavel" in a for a in ok)
