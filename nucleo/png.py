"""Leitura mínima de PNG (sem Pillow): dimensões e transparência."""
import struct
import zlib

ASSINATURA = b"\x89PNG\r\n\x1a\n"


def _chunks(dados: bytes):
    i = 8
    while i + 8 <= len(dados):
        n = struct.unpack(">I", dados[i:i + 4])[0]
        yield dados[i + 4:i + 8], dados[i + 8:i + 8 + n]
        i += 12 + n


def dimensoes(dados: bytes) -> "tuple[int, int] | None":
    if not dados.startswith(ASSINATURA) or len(dados) < 24:
        return None
    return struct.unpack(">II", dados[16:24])


def tem_alfa(dados: bytes) -> bool:
    """Color type 4 (cinza + alfa) ou 6 (RGBA)."""
    return dados.startswith(ASSINATURA) and len(dados) > 25 and dados[25] in (4, 6)


def cantos_transparentes(dados: bytes, limite: int = 16) -> bool:
    """Confere o alfa dos dois cantos de cima (primeira linha). Só decodifica PNG de 8 bits sem
    entrelaçamento; outros PNGs com alfa passam sem conferência."""
    if not tem_alfa(dados):
        return False
    w, _ = dimensoes(dados)
    if w is None:
        return False
    try:
        profundidade, tipo, entrelacado = dados[24], dados[25], dados[28]
    except IndexError:
        return False
    if profundidade != 8 or entrelacado != 0:
        return True
    canais = 4 if tipo == 6 else 2
    tamanho = w * canais

    # Valida que a PNG tem chunk IEND (está completa)
    chunks_list = list(_chunks(dados))
    if not any(t == b"IEND" for t, d in chunks_list):
        return False

    idat = b"".join(d for t, d in chunks_list if t == b"IDAT")
    try:
        bruto = zlib.decompressobj().decompress(idat, 1 + tamanho)
    except zlib.error:
        return False
    if len(bruto) < 1 + tamanho:
        return False
    filtro, linha = bruto[0], bytearray(bruto[1:1 + tamanho])
    # primeira linha: não há linha anterior, então Up = nenhum, Paeth = Sub e Average usa esquerda // 2
    if filtro in (1, 4):
        for k in range(canais, tamanho):
            linha[k] = (linha[k] + linha[k - canais]) & 0xFF
    elif filtro == 3:
        for k in range(canais, tamanho):
            linha[k] = (linha[k] + linha[k - canais] // 2) & 0xFF
    elif filtro not in (0, 2):
        return False
    return linha[canais - 1] <= limite and linha[-1] <= limite
