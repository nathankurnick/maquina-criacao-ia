"""Mockups com fundo transparente pra página de vendas.

Modo código: cenas em HTML/CSS capturadas pelo Chromium (Playwright) com omit_background.
Modo KIE (gerar_mockup, Task 3): Nano Banana monta a cena com as capas reais e o Recraft tira o fundo.
"""
import html
import os
from pathlib import Path

from nucleo.paletas import paleta

CSS = Path(__file__).with_name("mockup.css")
TAMANHO = {"pack": (1200, 1200), "livro": (1200, 1200), "pagina": (900, 1200), "capa": (1240, 1754)}
MAX_BONUS_PACK = 4


def e(t) -> str:
    return html.escape(str(t or ""), quote=True)


def _doc(corpo: str, paleta_nome: str, largura: int, altura: int) -> str:
    cores = paleta(paleta_nome)
    variaveis = ":root{" + ";".join(f"--pg-{k}:{v}" for k, v in cores.items()) + "}"
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>{variaveis}\n'
            f"{CSS.read_text(encoding='utf-8')}\n.palco{{width:{largura}px;height:{altura}px}}</style></head>"
            f"<body>{corpo}</body></html>")


def _livro(src: str, classe: str = "") -> str:
    classes = f"livro {classe}".strip()
    return (f'<div class="{classes}"><div class="lombada"></div>'
            f"<div class=\"frente\" style=\"background-image:url('{e(src)}')\"></div></div>")


def html_livro(capa_src: str, paleta_nome: str) -> str:
    w, h = TAMANHO["livro"]
    return _doc(f'<div class="palco cena"><div class="sombra"></div>{_livro(capa_src)}</div>', paleta_nome, w, h)


def html_pack(principal_src: str, bonus_srcs: "list[str]", paleta_nome: str) -> str:
    w, h = TAMANHO["pack"]
    extras = "".join(_livro(src, f"extra extra-{n}")
                     for n, src in enumerate(bonus_srcs[:MAX_BONUS_PACK], 1))
    return _doc(f'<div class="palco cena pack"><div class="sombra"></div>{extras}'
                f'{_livro(principal_src, "principal")}</div>', paleta_nome, w, h)


def html_pagina(img_src: str, paleta_nome: str) -> str:
    w, h = TAMANHO["pagina"]
    return _doc(f'<div class="palco"><div class="folha"><img src="{e(img_src)}" alt=""></div></div>',
                paleta_nome, w, h)


def html_capa_simples(titulo: str, rotulo: str, paleta_nome: str) -> str:
    w, h = TAMANHO["capa"]
    classe = ' class="longo"' if len(str(titulo or "")) > 40 else ""
    return _doc(f'<div class="capa-simples"><div class="faixa"></div><p class="rotulo">{e(rotulo)}</p>'
                f"<h1{classe}>{e(titulo)}</h1></div>", paleta_nome, w, h)


def capturar(doc: str, destino: Path, largura: int, altura: int, jpeg: bool = False, elemento: str = "") -> Path:
    """Renderiza `doc` no Chromium e grava em `destino` (troca atômica). PNG sai com fundo transparente;
    com jpeg=True e `elemento` (seletor CSS), grava só aquele elemento em JPEG."""
    from playwright.sync_api import sync_playwright

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp_html = destino.with_name(f".{destino.stem}.render.html")
    tmp_img = destino.with_name(f".{destino.stem}.novo{destino.suffix}")
    try:
        tmp_html.write_text(doc, encoding="utf-8")
        with sync_playwright() as p:
            nav = p.chromium.launch()
            try:
                pg = nav.new_page(viewport={"width": largura, "height": altura})
                pg.goto(tmp_html.as_uri(), wait_until="load")
                opcoes = {"path": str(tmp_img)}
                if jpeg:
                    opcoes.update(type="jpeg", quality=85)
                else:
                    opcoes["omit_background"] = True
                if elemento:
                    pg.query_selector(elemento).screenshot(**opcoes)
                else:
                    pg.screenshot(clip={"x": 0, "y": 0, "width": largura, "height": altura}, **opcoes)
            finally:
                try:
                    nav.close()
                except Exception:
                    pass
        os.replace(tmp_img, destino)
    finally:
        tmp_html.unlink(missing_ok=True)
        tmp_img.unlink(missing_ok=True)
    return destino


def gerar_capa_simples(titulo: str, rotulo: str, destino: Path, paleta_nome: str) -> Path:
    w, h = TAMANHO["capa"]
    return capturar(html_capa_simples(titulo, rotulo, paleta_nome), destino, w, h)


def via_codigo(tipo: str, entradas: "list[Path]", destino: Path, paleta_nome: str) -> Path:
    srcs = [Path(p).resolve().as_uri() for p in entradas]
    if tipo == "livro":
        doc = html_livro(srcs[0], paleta_nome)
    elif tipo == "pack":
        doc = html_pack(srcs[0], srcs[1:], paleta_nome)
    elif tipo == "pagina":
        doc = html_pagina(srcs[0], paleta_nome)
    else:
        raise ValueError(f"Tipo de mockup desconhecido: {tipo}")
    w, h = TAMANHO[tipo]
    return capturar(doc, destino, w, h)
