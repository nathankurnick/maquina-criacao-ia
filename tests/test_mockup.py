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
