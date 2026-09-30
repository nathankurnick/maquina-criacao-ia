import pytest

from nucleo import mockup, png


def _png_real(tmp_path, nome="capa.png", w=40, h=56):
    import struct
    import zlib

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    linha = b"\x00" + bytes([200, 60, 30]) * w
    arq = tmp_path / nome
    arq.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(linha * h)) + chunk(b"IEND", b""))
    return arq


def _ou_pular(fn, *a):
    pytest.importorskip("playwright")
    try:
        return fn(*a)
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium do Playwright não instalado")
        raise


def test_html_livro_usa_capa_e_paleta():
    h = mockup.html_livro("capa.png", "preto-dourado")
    assert "url('capa.png')" in h and 'class="livro"' in h and "--pg-destaque:#d4af37" in h


def test_html_pack_limita_bonus():
    h = mockup.html_pack("p.png", [f"b{i}.png" for i in range(7)], "azul-laranja")
    assert h.count('class="livro') == 1 + mockup.MAX_BONUS_PACK
    assert "url('b3.png')" in h and "url('b4.png')" not in h


def test_html_pagina_e_capa_simples_escapam():
    assert '<img src="p&lt;1&gt;.png"' in mockup.html_pagina("p<1>.png", "azul-laranja")
    h = mockup.html_capa_simples("Guia <do> Pão", "Bônus #1", "verde-branco")
    assert "Guia &lt;do&gt; Pão" in h and "Bônus #1" in h


@pytest.mark.parametrize("tipo", ["livro", "pack", "pagina"])
def test_via_codigo_gera_png_transparente(tmp_path, tipo):
    capa = _png_real(tmp_path)
    destino = tmp_path / "saida" / f"{tipo}.png"
    _ou_pular(mockup.via_codigo, tipo, [capa, capa], destino, "azul-laranja")
    dados = destino.read_bytes()
    assert png.dimensoes(dados) == mockup.TAMANHO[tipo]
    assert png.tem_alfa(dados) and png.cantos_transparentes(dados)
    assert sorted(p.name for p in destino.parent.iterdir()) == [f"{tipo}.png"]


def test_gerar_capa_simples(tmp_path):
    destino = tmp_path / "c.png"
    _ou_pular(mockup.gerar_capa_simples, "Checklist da obra", "Bônus #2", destino, "grafite-ciano")
    assert png.dimensoes(destino.read_bytes()) == mockup.TAMANHO["capa"]


def test_capturar_jpeg_do_elemento(tmp_path):
    capa = _png_real(tmp_path, w=300, h=420)
    doc = f'<!doctype html><body style="margin:0"><img id="i" style="display:block;width:150px" src="{capa.as_uri()}"></body>'
    destino = tmp_path / "menor.jpg"
    _ou_pular(mockup.capturar, doc, destino, 400, 400, True, "#i")
    assert destino.read_bytes()[:3] == b"\xff\xd8\xff"


import json

from nucleo import kie


class _Kie:
    """Simula a KIE: registra chamadas; `falhar` = exceção a levantar em alguma etapa."""

    def __init__(self, monkeypatch, falhar_em="", erro=None):
        self.chamadas = []
        self.falhar_em, self.erro = falhar_em, erro

        def etapa(nome, retorno):
            def f(*a, **k):
                self.chamadas.append((nome, a, k))
                if self.falhar_em == nome:
                    raise self.erro
                return retorno(*a, **k) if callable(retorno) else retorno
            return f

        def remover(chave, url, destino, limite=120):
            destino.write_bytes(b"kie-png")
            return destino

        monkeypatch.setattr(mockup, "_reduzir", lambda origem, destino: destino.write_bytes(b"\xff\xd8\xff") and destino)
        monkeypatch.setattr(kie, "enviar_arquivo", etapa("enviar", lambda chave, arq: f"https://f/{arq.name}"))
        monkeypatch.setattr(kie, "gerar_imagem_url", etapa("gerar", "https://r/cena.png"))
        monkeypatch.setattr(kie, "remover_fundo", etapa("remover", remover))

    def nomes(self):
        return [c[0] for c in self.chamadas]


def _codigo_falso(monkeypatch):
    feitos = []
    monkeypatch.setattr(mockup, "via_codigo",
                        lambda tipo, entradas, destino, paleta_nome: feitos.append(tipo) or destino.write_bytes(b"cod") or destino)
    return feitos


def test_kie_feliz(tmp_path, monkeypatch):
    k = _Kie(monkeypatch)
    _codigo_falso(monkeypatch)
    capas = [_png_real(tmp_path, "p.png"), _png_real(tmp_path, "b1.png")]
    r = mockup.gerar_mockup("pack", capas, tmp_path / "m" / "topo.png", "azul-laranja", chave="k")
    assert r["modo"] == "kie" and r["aviso"] == "" and r["permanente"] is False
    assert (tmp_path / "m" / "topo.png").read_bytes() == b"kie-png"
    assert k.nomes() == ["enviar", "enviar", "gerar", "remover"]
    gerar = k.chamadas[2]
    assert gerar[2]["referencias"] == ["https://f/ref-0.jpg", "https://f/ref-1.jpg"]
    assert "bonus" in gerar[1][1].lower()  # prompt do pack menciona os bônus
    assert not (tmp_path / "m" / ".mockup-tmp").exists()


@pytest.mark.parametrize("etapa", ["enviar", "gerar", "remover"])
def test_falha_em_qualquer_etapa_cai_no_codigo(tmp_path, monkeypatch, etapa):
    _Kie(monkeypatch, falhar_em=etapa, erro=kie.KieErro("A KIE está instável"))
    feitos = _codigo_falso(monkeypatch)
    r = mockup.gerar_mockup("livro", [_png_real(tmp_path)], tmp_path / "b.png", "azul-laranja", chave="k")
    assert r["modo"] == "codigo" and "instável" in r["aviso"] and r["permanente"] is False
    assert feitos == ["livro"]


def test_erro_permanente_marca_permanente(tmp_path, monkeypatch):
    _Kie(monkeypatch, falhar_em="gerar", erro=kie.KieErroPermanente("Seus créditos da KIE acabaram."))
    _codigo_falso(monkeypatch)
    r = mockup.gerar_mockup("livro", [_png_real(tmp_path)], tmp_path / "b.png", "azul-laranja", chave="k")
    assert r["modo"] == "codigo" and r["permanente"] is True and "créditos" in r["aviso"]


def test_erro_inesperado_vai_pro_log(tmp_path, monkeypatch, ambiente):
    _Kie(monkeypatch, falhar_em="gerar", erro=RuntimeError("boom"))
    _codigo_falso(monkeypatch)
    r = mockup.gerar_mockup("livro", [_png_real(tmp_path)], tmp_path / "b.png", "azul-laranja", chave="k")
    assert r["modo"] == "codigo" and "log" in r["aviso"]
    assert "boom" in (ambiente / "home" / "log" / "maquina.log").read_text(encoding="utf-8")


def test_sem_chave_e_pagina_sao_codigo(tmp_path, monkeypatch):
    k = _Kie(monkeypatch)
    feitos = _codigo_falso(monkeypatch)
    capa = _png_real(tmp_path)
    assert mockup.gerar_mockup("livro", [capa], tmp_path / "a.png", "azul-laranja")["modo"] == "codigo"
    assert mockup.gerar_mockup("pagina", [capa], tmp_path / "p.png", "azul-laranja", chave="k")["modo"] == "codigo"
    assert k.nomes() == [] and feitos == ["livro", "pagina"]


def test_cache_evita_nova_chamada_e_refazer_ignora(tmp_path, monkeypatch):
    k = _Kie(monkeypatch)
    _codigo_falso(monkeypatch)
    capa, destino = _png_real(tmp_path), tmp_path / "m" / "b.png"
    assert mockup.gerar_mockup("livro", [capa], destino, "azul-laranja", chave="k")["modo"] == "kie"
    assert mockup.gerar_mockup("livro", [capa], destino, "azul-laranja", chave="k")["modo"] == "cache"
    assert json.loads((tmp_path / "m" / mockup.CACHE).read_text())["b.png"]["modo"] == "kie"
    assert mockup.gerar_mockup("livro", [capa], destino, "azul-laranja", chave="k", refazer=True)["modo"] == "kie"
    assert k.nomes().count("gerar") == 2


def test_cache_invalida_se_capa_ou_paleta_muda(tmp_path, monkeypatch):
    k = _Kie(monkeypatch)
    _codigo_falso(monkeypatch)
    capa, destino = _png_real(tmp_path), tmp_path / "b.png"
    mockup.gerar_mockup("livro", [capa], destino, "azul-laranja", chave="k")
    mockup.gerar_mockup("livro", [capa], destino, "preto-dourado", chave="k")
    capa.write_bytes(capa.read_bytes() + b"\x00")
    mockup.gerar_mockup("livro", [capa], destino, "preto-dourado", chave="k")
    assert k.nomes().count("gerar") == 3


def test_codigo_em_cache_e_refeito_quando_chega_a_chave(tmp_path, monkeypatch):
    k = _Kie(monkeypatch)
    _codigo_falso(monkeypatch)
    capa, destino = _png_real(tmp_path), tmp_path / "b.png"
    assert mockup.gerar_mockup("livro", [capa], destino, "azul-laranja")["modo"] == "codigo"
    assert mockup.gerar_mockup("livro", [capa], destino, "azul-laranja")["modo"] == "cache"
    assert mockup.gerar_mockup("livro", [capa], destino, "azul-laranja", chave="k")["modo"] == "kie"


def test_entrada_inexistente_e_tipo_invalido(tmp_path):
    with pytest.raises(ValueError, match="Não achei"):
        mockup.gerar_mockup("livro", [tmp_path / "nada.png"], tmp_path / "b.png", "azul-laranja")
    with pytest.raises(ValueError):
        mockup.gerar_mockup("poster", [_png_real(tmp_path)], tmp_path / "b.png", "azul-laranja")
