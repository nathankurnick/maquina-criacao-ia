"""Mockups com fundo transparente pra página de vendas.

Modo código: cenas em HTML/CSS capturadas pelo Chromium (Playwright) com omit_background.
Modo KIE (gerar_mockup, Task 3): Nano Banana monta a cena com as capas reais e o Recraft tira o fundo.
"""
import hashlib
import html
import json
import os
import shutil
import traceback
from pathlib import Path

from nucleo import kie
from nucleo.erros import registrar_log
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


TIPOS = ("pack", "livro", "pagina")
CACHE = ".mockups.json"
VERSAO_PROMPT = 1
_FUNDO = ("Plain solid light gray seamless studio background, soft natural shadow under the objects, "
          "no other objects, no hands, no people, no added text, logos or watermarks.")
_PROMPT_LIVRO = ("Photorealistic product mockup of the book in the reference image: one hardcover book standing "
                 "slightly turned to the right, cover facing the camera, reproducing the cover artwork and every "
                 "word of its text exactly as in the reference. " + _FUNDO)
_PROMPT_PACK = ("Photorealistic digital product bundle mockup. The first reference image is the cover of the main "
                "product: show it as a large hardcover book in the front center and also on a tablet screen "
                "standing behind it. {bonus}Reproduce every cover exactly as in the references, without changing "
                "any word. " + _FUNDO)
_PROMPT_BONUS = ("The other {n} reference images are bonus covers: show each one as a smaller book arranged "
                 "around the main book. ")


def _prompt(tipo: str, n_refs: int) -> str:
    if tipo == "livro":
        return _PROMPT_LIVRO
    bonus = _PROMPT_BONUS.format(n=n_refs - 1) if n_refs > 1 else ""
    return _PROMPT_PACK.format(bonus=bonus)


def _hash(tipo: str, entradas: "list[Path]", paleta_nome: str) -> str:
    h = hashlib.sha256(f"{tipo}|{VERSAO_PROMPT}|{paleta_nome}".encode())
    for p in entradas:
        h.update(b"|")
        h.update(p.read_bytes())
    return h.hexdigest()


def _ler_cache(pasta: Path) -> dict:
    try:
        d = json.loads((pasta / CACHE).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _gravar_cache(pasta: Path, nome: str, h: str, modo: str) -> None:
    c = _ler_cache(pasta)
    c[nome] = {"hash": h, "modo": modo}
    tmp = pasta / f"{CACHE}.novo"
    tmp.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, pasta / CACHE)


def _reduzir(origem: Path, destino: Path) -> Path:
    """JPEG de 1000 px de largura pra subir na KIE (capas de 1240x1754 em PNG passam de alguns MB)."""
    doc = ('<!doctype html><body style="margin:0"><img id="i" style="display:block;width:1000px" '
           f'src="{e(Path(origem).resolve().as_uri())}"></body>')
    return capturar(doc, destino, 1000, 1500, jpeg=True, elemento="#i")


def _via_kie(tipo: str, entradas: "list[Path]", destino: Path, chave: str) -> None:
    tmp = destino.parent / ".mockup-tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        refs = []
        for k, arq in enumerate(entradas[:1 + MAX_BONUS_PACK]):
            refs.append(kie.enviar_arquivo(chave, _reduzir(arq, tmp / f"ref-{k}.jpg")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    url = kie.gerar_imagem_url(chave, _prompt(tipo, len(refs)), "1:1", referencias=refs)
    kie.remover_fundo(chave, url, destino)


def gerar_mockup(tipo: str, entradas: "list[Path]", destino: Path, paleta_nome: str,
                 chave: "str | None" = None, refazer: bool = False) -> dict:
    """Gera o mockup em `destino` (PNG transparente). Página interna é sempre por código.
    Qualquer falha da KIE cai pro modo código e volta como `aviso`; `permanente` avisa o chamador
    que repetir na KIE não adianta (chave recusada, sem créditos)."""
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de mockup desconhecido: {tipo}")
    entradas, destino = [Path(p) for p in entradas], Path(destino)
    faltando = [p for p in entradas if not p.is_file()]
    if not entradas or faltando:
        raise ValueError(f"Não achei a imagem {faltando[0] if faltando else '(nenhuma)'} pro mockup.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    usa_kie = bool(chave) and tipo != "pagina"
    h = _hash(tipo, entradas, paleta_nome)
    anterior = _ler_cache(destino.parent).get(destino.name)
    if (not refazer and destino.exists() and isinstance(anterior, dict) and anterior.get("hash") == h
            and (anterior.get("modo") == "kie" or not usa_kie)):
        return {"arquivo": destino, "modo": "cache", "aviso": "", "permanente": False}
    aviso, permanente = "", False
    if usa_kie:
        try:
            _via_kie(tipo, entradas, destino, chave)
            _gravar_cache(destino.parent, destino.name, h, "kie")
            return {"arquivo": destino, "modo": "kie", "aviso": "", "permanente": False}
        except KeyboardInterrupt:
            raise
        except kie.KieErroPermanente as err:
            aviso, permanente = str(err), True
        except kie.KieErro as err:
            aviso = str(err)
        except Exception:  # noqa: BLE001 — mockup nunca derruba a página
            try:
                registrar_log(traceback.format_exc())
            except Exception:
                pass
            aviso = "erro inesperado na KIE (detalhes no log da Máquina)"
    via_codigo(tipo, entradas, destino, paleta_nome)
    _gravar_cache(destino.parent, destino.name, h, "codigo")
    return {"arquivo": destino, "modo": "codigo", "aviso": aviso, "permanente": permanente}
