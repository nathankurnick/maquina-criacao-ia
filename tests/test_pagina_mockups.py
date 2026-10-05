import json

import pagina_mockups as pm


def _projeto(tmp_path, bonus=2, fotos=3, hero_entregavel="pack", capa_principal=True):
    p = tmp_path / "proj"
    (p / "pagina" / "imagens" / "carrossel").mkdir(parents=True)
    conteudo = {"hero": {"headline": "Casas **de campo**", "entregavel": hero_entregavel},
                "bonus": {"itens": [{"titulo": f"Bônus {n}", "entregavel": "guia" if n == 1 else ""}
                                    for n in range(1, bonus + 1)]},
                "rodape": {"nomeProduto": "Pack Refúgio"}}
    (p / "pagina" / "conteudo.json").write_text(json.dumps(conteudo), encoding="utf-8")
    for slug in (["pack"] if capa_principal else []) + ["guia"]:
        (p / "entregaveis" / slug).mkdir(parents=True)
        (p / "entregaveis" / slug / "capa.png").write_bytes(b"\x89PNG\r\n\x1a\ncapa-" + slug.encode())
    for k in range(fotos):
        (p / "pagina" / "imagens" / "carrossel" / f"0{k}-x.png").write_bytes(b"\x89PNG\r\n\x1a\nf")
    return p


def test_planejar(tmp_path):
    plano = pm.planejar(_projeto(tmp_path, bonus=2, fotos=8))
    assert plano["topo"]["ativo"] and plano["topo"]["capa"].name == "capa.png"
    assert [b["capa"] is not None for b in plano["bonus"]] == [True, False]
    assert len(plano["paginas"]) == pm.MAX_PAGINAS == 6
    assert plano["kie"] == 3 and plano["avisos"] == []


def test_planejar_avisa_capa_principal_faltando(tmp_path):
    plano = pm.planejar(_projeto(tmp_path, capa_principal=False))
    assert plano["topo"]["capa"] is None and "entregaveis/pack/capa.png" in plano["avisos"][0]


def test_gerar_monta_tudo_e_para_kie_em_erro_permanente(tmp_path, monkeypatch):
    chamadas = []

    def falso(tipo, entradas, destino, paleta_nome, chave=None, refazer=False):
        chamadas.append((tipo, destino.name, chave, [p.name for p in entradas]))
        destino.write_bytes(b"m")
        permanente = chave is not None and tipo == "pack"
        return {"arquivo": destino, "modo": "codigo" if permanente or not chave else "kie",
                "aviso": "Seus créditos da KIE acabaram." if permanente else "", "permanente": permanente}

    monkeypatch.setattr(pm, "gerar_mockup", falso)
    monkeypatch.setattr(pm, "gerar_capa_simples",
                        lambda titulo, rotulo, destino, paleta_nome: destino.parent.mkdir(parents=True, exist_ok=True)
                        or (destino.write_bytes(b"c") and destino))
    p = _projeto(tmp_path, bonus=2, fotos=2)
    r = pm.gerar(pm.planejar(p), "azul-laranja", "k")
    assert [c[:2] for c in chamadas] == [("pack", "topo.png"), ("livro", "bonus-1.png"), ("livro", "bonus-2.png"),
                                         ("pagina", "pagina-01.png"), ("pagina", "pagina-02.png")]
    assert chamadas[0][2] == "k" and all(c[2] is None for c in chamadas[1:])  # parou de usar a KIE
    assert len(chamadas[0][3]) == 3  # principal + 2 capas de bônus
    assert any("créditos" in a for a in r["avisos"])


def test_gerar_apaga_sobras(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "gerar_mockup", lambda tipo, entradas, destino, paleta_nome, chave=None, refazer=False:
                        destino.write_bytes(b"m") and {"arquivo": destino, "modo": "codigo", "aviso": "", "permanente": False})
    monkeypatch.setattr(pm, "gerar_capa_simples", lambda titulo, rotulo, destino, paleta_nome:
                        destino.parent.mkdir(parents=True, exist_ok=True) or (destino.write_bytes(b"c") and destino))
    p = _projeto(tmp_path, bonus=1, fotos=1)
    saida = p / "pagina" / "imagens" / "mockups"
    saida.mkdir(parents=True)
    for velho in ("bonus-2.png", "bonus-3.png", "pagina-02.png"):
        (saida / velho).write_bytes(b"v")
    pm.gerar(pm.planejar(p), "azul-laranja", None)
    assert sorted(x.name for x in saida.iterdir() if not x.name.startswith(".")) == ["bonus-1.png", "pagina-01.png", "topo.png"]


def test_capa_simples_reaproveitada_se_titulo_nao_muda(tmp_path, monkeypatch):
    feitas = []
    monkeypatch.setattr(pm, "gerar_mockup", lambda tipo, entradas, destino, paleta_nome, chave=None, refazer=False:
                        destino.write_bytes(b"m") and {"arquivo": destino, "modo": "codigo", "aviso": "", "permanente": False})
    monkeypatch.setattr(pm, "gerar_capa_simples", lambda titulo, rotulo, destino, paleta_nome:
                        feitas.append(titulo) or destino.parent.mkdir(parents=True, exist_ok=True) or (destino.write_bytes(b"c") and destino))
    p = _projeto(tmp_path, bonus=2, fotos=0)
    pm.gerar(pm.planejar(p), "azul-laranja", None)
    pm.gerar(pm.planejar(p), "azul-laranja", None)
    assert feitas == ["Bônus 2"]


def test_main_estimar_sem_chave(tmp_path, ambiente, capsys):
    p = _projeto(tmp_path, bonus=2, fotos=2)
    assert pm.main(["--projeto", str(p), "--estimar"]) == 0
    out = capsys.readouterr().out
    assert "grátis" in out and not (p / "pagina" / "imagens" / "mockups" / "topo.png").exists()


def test_main_estimar_com_chave_mostra_saldo(tmp_path, ambiente, monkeypatch, capsys):
    monkeypatch.setattr(pm, "obter_chave", lambda nome: "k")
    monkeypatch.setattr(pm.kie, "creditos", lambda chave: 812.0)
    assert pm.main(["--projeto", str(_projeto(tmp_path)), "--estimar"]) == 0
    out = capsys.readouterr().out
    assert "3 gerações" in out and "3 remoções de fundo" in out and "812" in out


def test_main_sem_kie_e_erros(tmp_path, ambiente, monkeypatch, capsys):
    usados = []
    monkeypatch.setattr(pm, "obter_chave", lambda nome: "k")
    monkeypatch.setattr(pm, "gerar", lambda plano, paleta_nome, chave, refazer=False:
                        usados.append(chave) or {"modos": [], "avisos": []})
    p = _projeto(tmp_path)
    assert pm.main(["--projeto", str(p), "--sem-kie"]) == 0 and usados == [None]
    assert pm.main(["--projeto", str(tmp_path / "nada")]) == 1
    assert "conteudo.json" in capsys.readouterr().err
    assert pm.main([]) == 1


def _fakes(monkeypatch, chamadas, perm_pack=False):
    def falso(tipo, entradas, destino, paleta_nome, chave=None, refazer=False):
        chamadas.append((tipo, destino.name, chave, [p.name for p in entradas]))
        destino.write_bytes(b"m")
        perm = perm_pack and chave is not None and tipo == "pack"
        return {"arquivo": destino, "modo": "codigo" if perm or not chave else "kie",
                "aviso": "Seus créditos da KIE acabaram." if perm else "", "permanente": perm}
    monkeypatch.setattr(pm, "gerar_mockup", falso)
    monkeypatch.setattr(pm, "gerar_capa_simples", lambda titulo, rotulo, destino, paleta_nome:
                        destino.parent.mkdir(parents=True, exist_ok=True) or (destino.write_bytes(b"c") and destino))


def test_paginas_nunca_usam_kie(tmp_path, monkeypatch):
    chamadas = []
    _fakes(monkeypatch, chamadas)
    pm.gerar(pm.planejar(_projeto(tmp_path, bonus=1, fotos=2)), "azul-laranja", "k")
    assert [c[2] for c in chamadas if c[0] == "pagina"] == [None, None]
    assert all(c[2] == "k" for c in chamadas if c[0] != "pagina")


def test_aviso_conta_todas_as_capas_em_codigo(tmp_path, monkeypatch):
    _fakes(monkeypatch, [], perm_pack=True)
    r = pm.gerar(pm.planejar(_projeto(tmp_path, bonus=2, fotos=1)), "azul-laranja", "k")
    aviso = [a for a in r["avisos"] if "modo código" in a]
    assert len(aviso) == 1 and aviso[0].startswith("⚠️ 3 mockup(s)") and "créditos" in aviso[0]


def test_hero_inativo(tmp_path, monkeypatch):
    chamadas = []
    _fakes(monkeypatch, chamadas)
    p = _projeto(tmp_path, bonus=1, fotos=0, capa_principal=False)
    c = json.loads((p / "pagina" / "conteudo.json").read_text(encoding="utf-8"))
    c["hero"]["ativo"] = False
    (p / "pagina" / "conteudo.json").write_text(json.dumps(c), encoding="utf-8")
    saida = p / "pagina" / "imagens" / "mockups"
    saida.mkdir(parents=True)
    (saida / "topo.png").write_bytes(b"velho")
    plano = pm.planejar(p)
    assert plano["avisos"] == [] and plano["kie"] == 1
    pm.gerar(plano, "azul-laranja", None)
    assert not (saida / "topo.png").exists() and [c[0] for c in chamadas] == ["livro"]


def test_sem_bonus_pack_so_com_principal(tmp_path, monkeypatch):
    chamadas = []
    _fakes(monkeypatch, chamadas)
    p = _projeto(tmp_path, bonus=1, fotos=0)
    c = json.loads((p / "pagina" / "conteudo.json").read_text(encoding="utf-8"))
    c["bonus"]["ativo"] = False
    (p / "pagina" / "conteudo.json").write_text(json.dumps(c), encoding="utf-8")
    pm.gerar(pm.planejar(p), "azul-laranja", None)
    assert [(c[0], len(c[3])) for c in chamadas] == [("pack", 1)]
    assert not list((p / "pagina" / "imagens" / "mockups").glob("bonus-*.png"))


def test_limpa_capas_antigas(tmp_path, monkeypatch):
    _fakes(monkeypatch, [])
    p = _projeto(tmp_path, bonus=1, fotos=0)
    capas = p / "pagina" / "imagens" / "mockups" / ".capas"
    capas.mkdir(parents=True)
    (capas / "bonus-3-abc.png").write_bytes(b"v")
    (capas / "principal-abc.png").write_bytes(b"v")
    pm.gerar(pm.planejar(p), "azul-laranja", None)
    assert list(capas.glob("*.png")) == []


def test_estimar_nao_aborta_se_saldo_falha(tmp_path, ambiente, monkeypatch, capsys):
    monkeypatch.setattr(pm, "obter_chave", lambda nome: "k")
    def quebra(chave):
        raise OSError("rede")
    monkeypatch.setattr(pm.kie, "creditos", quebra)
    assert pm.main(["--projeto", str(_projeto(tmp_path)), "--estimar"]) == 0
    assert "Não consegui ver o saldo" in capsys.readouterr().out


def test_execucao_real_mostra_estimativa_antes(tmp_path, ambiente, monkeypatch, capsys):
    monkeypatch.setattr(pm, "obter_chave", lambda nome: "k")
    monkeypatch.setattr(pm.kie, "creditos", lambda chave: 5.0)
    monkeypatch.setattr(pm, "gerar", lambda plano, paleta_nome, chave, refazer=False: {"modos": [], "avisos": []})
    assert pm.main(["--projeto", str(_projeto(tmp_path))]) == 0
    assert "gerações" in capsys.readouterr().out


def test_paleta_efetiva_cadeia(tmp_path, ambiente):
    p = _projeto(tmp_path)
    pag = p / "pagina"
    assert pm._paleta_efetiva(p, pag) == pm.PALETA_PADRAO
    (p / "oferta.md").write_text("---\nnome: X\npaleta: preto-dourado\n---\ncorpo\n", encoding="utf-8")
    assert pm._paleta_efetiva(p, pag) == "preto-dourado"
    (pag / "config.json").write_text(json.dumps({"paleta": "verde-branco"}), encoding="utf-8")
    assert pm._paleta_efetiva(p, pag) == "verde-branco"
    (pag / "config.json").write_text(json.dumps({"paleta": "nao-existe"}), encoding="utf-8")
    assert pm._paleta_efetiva(p, pag) == "preto-dourado"


def test_main_usa_paleta_da_oferta_e_aceita_pagina(tmp_path, ambiente, monkeypatch):
    p = _projeto(tmp_path)
    (p / "oferta.md").write_text("---\nnome: X\npaleta: preto-dourado\n---\ncorpo\n", encoding="utf-8")
    visto = {}
    monkeypatch.setattr(pm, "gerar", lambda plano, paleta_nome, chave, refazer=False:
                        visto.update(paleta=paleta_nome, saida=plano["saida"]) or {"modos": [], "avisos": []})
    assert pm.main(["--projeto", str(p), "--sem-kie"]) == 0 and visto["paleta"] == "preto-dourado"
    outra = p / "funil" / "extra"
    (outra / "imagens").mkdir(parents=True)
    (outra / "conteudo.json").write_text(json.dumps({"hero": {"headline": "X"}}), encoding="utf-8")
    assert pm.main(["--projeto", str(p), "--pagina", str(outra), "--sem-kie"]) == 0
    assert visto["saida"] == outra.resolve() / "imagens" / "mockups"


def test_cache_hit_limpa_aviso_de_carrossel_velho(tmp_path, ambiente, monkeypatch):
    import os
    import time

    import pagina_render as pr
    from nucleo import mockup
    p = _projeto(tmp_path, bonus=0, fotos=1, hero_entregavel="")
    monkeypatch.setattr(mockup, "via_codigo", lambda tipo, entradas, destino, paleta_nome:
                        destino.write_bytes(b"cod") and destino)
    assert pm.main(["--projeto", str(p), "--sem-kie"]) == 0
    m = p / "pagina" / "imagens" / "mockups" / "pagina-01.png"
    velho = time.time() - 500
    os.utime(m, (velho, velho))
    assert pm.main(["--projeto", str(p), "--sem-kie"]) == 0  # tudo em cache
    _, avisos = pr.montar_site(p)
    assert not any("mudaram depois dos mockups" in a for a in avisos)


def test_estimar_mostra_avisos_de_entregavel(tmp_path, ambiente, capsys):
    p = _projeto(tmp_path, capa_principal=False)
    c = json.loads((p / "pagina" / "conteudo.json").read_text(encoding="utf-8"))
    c["bonus"]["itens"][1]["entregavel"] = "Guia Ruim"
    (p / "pagina" / "conteudo.json").write_text(json.dumps(c), encoding="utf-8")
    assert pm.main(["--projeto", str(p), "--estimar"]) == 0
    out = capsys.readouterr().out
    assert "entregaveis/pack/capa.png" in out and 'bonus #2: "entregavel" inválido ("Guia Ruim")' in out
    assert out.count("Guia Ruim") == 1


def test_cartoes_com_arte_geram_foto_na_kie(tmp_path, monkeypatch):
    p = _projeto(tmp_path, bonus=0, fotos=0)
    dados = json.loads((p / "pagina" / "conteudo.json").read_text(encoding="utf-8"))
    dados["conteudo"] = {"itens": [{"titulo": "A", "arte": "a red trailer"}, {"titulo": "B"},
                                   {"titulo": "C", "arte": "x", "imagem": "c.png"}]}
    (p / "pagina" / "conteudo.json").write_text(json.dumps(dados), encoding="utf-8")
    (p / "pagina" / "imagens" / "conteudo").mkdir(parents=True)
    (p / "pagina" / "imagens" / "conteudo" / "c.png").write_bytes(b"c")
    plano = pm.planejar(p)
    assert [c["n"] for c in plano["cards"]] == [1]
    monkeypatch.setattr(pm, "gerar_mockup", lambda tipo, entradas, destino, paleta_nome, chave=None, refazer=False:
                        destino.write_bytes(b"m") and {"arquivo": destino, "modo": "kie", "aviso": "", "permanente": False})
    chamadas = []
    monkeypatch.setattr(pm.kie, "gerar_imagem", lambda chave, prompt, prop, destino, **kw:
                        chamadas.append((prompt, prop)) or destino.write_bytes(b"f"))
    r = pm.gerar(plano, "azul-laranja", "k")
    assert len(chamadas) == 1 and chamadas[0][1] == "4:3" and chamadas[0][0].startswith("a red trailer")
    assert ("conteudo-1.png", "kie") in r["modos"]
    r2 = pm.gerar(pm.planejar(p), "azul-laranja", "k")
    assert ("conteudo-1.png", "cache") in r2["modos"] and len(chamadas) == 1


def test_cartoes_sem_chave_avisam(tmp_path, monkeypatch):
    p = _projeto(tmp_path, bonus=0, fotos=0)
    dados = json.loads((p / "pagina" / "conteudo.json").read_text(encoding="utf-8"))
    dados["conteudo"] = {"itens": [{"titulo": "A", "arte": "x"}]}
    (p / "pagina" / "conteudo.json").write_text(json.dumps(dados), encoding="utf-8")
    monkeypatch.setattr(pm, "gerar_mockup", lambda tipo, entradas, destino, paleta_nome, chave=None, refazer=False:
                        destino.write_bytes(b"m") and {"arquivo": destino, "modo": "codigo", "aviso": "", "permanente": False})
    r = pm.gerar(pm.planejar(p), "azul-laranja", None)
    assert any("sem a chave da KIE" in a for a in r["avisos"])
    assert not (p / "pagina" / "imagens" / "mockups" / "conteudo-1.png").exists()
