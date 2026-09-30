import json

import pytest

import pagina_mockups as pm
from nucleo import mockup


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
