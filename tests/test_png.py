import struct
import zlib

from nucleo import png


def _png(w, h, tipo, pixel, filtro=0):
    canais = {2: 3, 6: 4, 4: 2}[tipo]
    assert len(pixel) == canais

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))

    linha = bytes([filtro]) + bytes(pixel) * w
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, tipo, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(linha * h)) + chunk(b"IEND", b""))


def test_dimensoes():
    assert png.dimensoes(_png(7, 3, 2, (1, 2, 3))) == (7, 3)
    assert png.dimensoes(b"nada") is None


def test_tem_alfa():
    assert png.tem_alfa(_png(2, 2, 6, (0, 0, 0, 0)))
    assert png.tem_alfa(_png(2, 2, 4, (0, 0)))
    assert not png.tem_alfa(_png(2, 2, 2, (0, 0, 0)))
    assert not png.tem_alfa(b"\xff\xd8\xff")


def test_cantos_transparentes():
    assert png.cantos_transparentes(_png(4, 4, 6, (255, 0, 0, 0)))
    assert not png.cantos_transparentes(_png(4, 4, 6, (255, 0, 0, 255)))
    assert not png.cantos_transparentes(_png(4, 4, 2, (255, 0, 0)))


def test_cantos_com_filtro_sub():
    # filtro Sub (1): cada byte guarda a diferença pro pixel da esquerda; tudo 0 = tudo transparente
    assert png.cantos_transparentes(_png(4, 4, 6, (0, 0, 0, 0), filtro=1))


def test_png_quebrado_nao_estoura():
    dados = _png(4, 4, 6, (0, 0, 0, 0))
    assert png.cantos_transparentes(dados[:60]) is False
