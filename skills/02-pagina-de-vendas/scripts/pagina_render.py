# skills/02-pagina-de-vendas/scripts/pagina_render.py
"""Monta o site estático da página de vendas (template do Gerador) na pasta do aluno.

Uso: python pagina_render.py --projeto <pasta do projeto> [--pagina <pasta da página>]
Lê <P>/pagina/conteudo.json, config.json e imagens/; recria <P>/pagina/site/.
"""
import argparse
import html
import json
import os
import re
import shutil
import struct
import sys
import traceback
from datetime import date, datetime
from pathlib import Path

from pagina_conteudo import ICONES, PALETA_PADRAO, PALETAS, ler_config, normalizar, url_segura

CSS = Path(__file__).resolve().parent.parent / "template" / "pagina.css"
EXT_FOTO = (".png", ".jpg", ".jpeg", ".webp")
EXT_LOGO = EXT_FOTO + (".svg",)


def _log_tecnico(texto: str) -> None:
    try:
        home = Path(os.environ.get("MAQUINA_HOME") or Path.home() / ".maquina")
        (home / "log").mkdir(parents=True, exist_ok=True)
        with (home / "log" / "maquina.log").open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] pagina_render: {texto}\n")
    except Exception:
        pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando incompleto ({message}). Use: pagina_render.py --projeto <pasta do projeto>",
              file=sys.stderr)
        raise SystemExit(1)


def e(texto: str) -> str:
    return html.escape(texto or "", quote=True)


def com_destaque(texto: str) -> str:
    partes = re.split(r"(\*\*[^*]+\*\*)", texto or "")
    saida = []
    for p in partes:
        if p.startswith("**") and p.endswith("**") and len(p) > 4:
            miolo = p[2:-2]
            saida.append(f'<span class="destaque">{e(miolo)}</span>' if miolo.strip() else e(miolo))
        else:
            saida.append(e(p.replace("**", "")))
    return "".join(saida)


# Fontes embutidas no site (licença OFL, em template/fontes/): nada de servidor de terceiros.
FONTES_DIR = CSS.parent / "fontes"
FONTES = ('<link rel="preload" href="fontes/archivo.woff2" as="font" type="font/woff2" crossorigin>\n'
          "<style>@font-face{font-family:Archivo;src:url(fontes/archivo.woff2) format('woff2');"
          "font-weight:100 900;font-stretch:62% 125%;font-display:swap}"
          "@font-face{font-family:Manrope;src:url(fontes/manrope.woff2) format('woff2');"
          "font-weight:200 800;font-display:swap}</style>\n")


def _icone(nome: str, classe: str = "icone") -> str:
    caminhos = "".join(f'<path d="{d}"/>' for d in ICONES.get(nome, ICONES["estrela"]))
    return (f'<svg class="{classe}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{caminhos}</svg>')


def _cta(href: str, texto: str) -> str:
    href = href if url_segura(href) else "#"
    return f'<a class="cta" href="{e(href)}">{e(texto)}</a>'


def _secao(classes: str, interno: str, id_: str = "") -> str:
    ident = f' id="{id_}"' if id_ else ""
    return f'<section class="secao {classes}"{ident}>{interno}</section>\n'


def _cabeca(b: dict) -> str:
    s = f"<h2>{e(b.get('titulo', ''))}</h2>"
    if b.get("subtitulo"):
        s += f'<p class="sub">{e(b["subtitulo"])}</p>'
    return s


def _dimensoes(arq: Path) -> "tuple[int, int] | None":
    """Largura e altura de PNG, JPEG ou WebP lendo só o cabeçalho; None se algo fugir do esperado."""
    try:
        with open(arq, "rb") as f:
            cab = f.read(32)
            if cab.startswith(b"\x89PNG\r\n\x1a\n") and len(cab) >= 24:
                return struct.unpack(">II", cab[16:24])
            if cab[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    m = f.read(2)
                    if len(m) < 2 or m[0] != 0xFF:
                        return None
                    if m[1] == 0xFF:
                        f.seek(-1, 1)
                        continue
                    if m[1] in (0xD8, 0x01) or 0xD0 <= m[1] <= 0xD7:
                        continue
                    tam = f.read(2)
                    if len(tam) < 2:
                        return None
                    n = struct.unpack(">H", tam)[0]
                    if m[1] in (0xC0, 0xC1, 0xC2):
                        d = f.read(5)
                        if len(d) < 5:
                            return None
                        h, w = struct.unpack(">HH", d[1:5])
                        return (w, h) if w and h else None
                    f.seek(n - 2, 1)
            if cab[:4] == b"RIFF" and cab[8:12] == b"WEBP" and len(cab) >= 30:
                tipo = cab[12:16]
                if tipo == b"VP8X":
                    return (int.from_bytes(cab[24:27], "little") + 1, int.from_bytes(cab[27:30], "little") + 1)
                if tipo == b"VP8L" and cab[20] == 0x2F:
                    v = int.from_bytes(cab[21:25], "little")
                    return ((v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1)
                if tipo == b"VP8 " and cab[23:26] == b"\x9d\x01\x2a":
                    return (struct.unpack("<H", cab[26:28])[0] & 0x3FFF, struct.unpack("<H", cab[28:30])[0] & 0x3FFF)
    except (OSError, struct.error, ValueError):
        return None
    return None


def _tam(src: str, tamanhos: dict) -> str:
    wh = tamanhos.get(src)
    return f' width="{wh[0]}" height="{wh[1]}"' if wh else ""


def _hero(b, logo, href, nome="", mockup="", tamanhos=None):
    if not b["ativo"]:
        return ""
    partes = []
    if logo:
        partes.append(f'<img class="logo" src="{e(logo)}" alt="{e(nome)}"{_tam(logo, tamanhos or {})}>')
    if b["badge"]:
        partes.append(f'<p class="badge">{e(b["badge"])}</p>')
    partes.append(f"<h1>{com_destaque(b['headline'])}</h1>")
    if b["subheadline"]:
        partes.append(f'<p class="subheadline">{e(b["subheadline"])}</p>')
    if not mockup:
        partes.append(_cta(href, b["cta"]))
        return _secao("escura hero", f'<div class="caixa caixa-estreita centro">{"".join(partes)}</div>')
    img = (f'<img class="hero-mockup" src="{e(mockup)}" alt="{e(nome or "Produto")}"'
           f'{_tam(mockup, tamanhos or {})} fetchpriority="high">')
    return _secao("escura hero", f'<div class="caixa hero-grade"><div class="hero-texto">{"".join(partes)}</div>'
                                 f'{img}<div class="hero-cta">{_cta(href, b["cta"])}</div></div>')


def _carrossel(b, imagens, mockup=False, tamanhos=None):
    if not b["ativo"] or not imagens:
        return ""
    fotos = "".join(f'<img src="{e(src)}" alt="Imagem {i} do material"{_tam(src, tamanhos or {})} loading="lazy">'
                    for i, src in enumerate(imagens, 1))
    desc = f'<p class="sub">{e(b["descricao"])}</p>' if b["descricao"] else ""
    classe = "carrossel carrossel-mockup" if mockup else "carrossel"
    return _secao("clara borda-topo",
                  f'<div class="caixa"><h2>{e(b["titulo"])}</h2>{desc}<div class="{classe}">{fotos}</div></div>')


def _para_quem(b, href):
    if not b["ativo"]:
        return ""
    cartoes = "".join(f'<div class="cartao cartao-claro"><h3>{e(i["titulo"])}</h3>'
                      f'<p class="desc">{e(i["descricao"])}</p></div>' for i in b["itens"])
    return _secao("branca", f'<div class="caixa">{_cabeca(b)}<div class="grade grade-3">{cartoes}</div>'
                            f'<div class="centro">{_cta(href, "QUERO ACESSAR AGORA")}</div></div>')


def _conteudo(b, fotos=None, tamanhos=None):
    if not b["ativo"]:
        return ""
    cartoes = []
    for n, i in enumerate(b["itens"], 1):
        src = (fotos or {}).get(n, "")
        texto = f'{_icone(i["icone"])}<h3>{e(i["titulo"])}</h3><p class="desc">{e(i["descricao"])}</p>'
        if src:
            cartoes.append(f'<div class="cartao cartao-vidro cartao-foto"><div class="foto"><img src="{e(src)}" '
                           f'alt="{e(i["titulo"])}"{_tam(src, tamanhos or {})} loading="lazy"></div>'
                           f'<div class="corpo">{texto}</div></div>')
        else:
            cartoes.append(f'<div class="cartao cartao-vidro">{texto}</div>')
    grade = "grade grade-2 grade-3l grade-fotos" if fotos else "grade grade-2 grade-3l"
    return _secao("media", f'<div class="caixa">{_cabeca(b)}<div class="{grade}">{"".join(cartoes)}</div></div>')


def _incluso(b):
    if not b["ativo"]:
        return ""
    itens = "".join(f'<li><span class="check" aria-hidden="true">{_icone("check", "icone-check")}</span><div>'
                    f'<p class="item-titulo">{e(i["titulo"])}</p><p class="desc">{e(i["descricao"])}</p></div></li>'
                    for i in b["itens"])
    nota = f'<p class="ficha-nota">{e(b["nota"])}</p>' if b["nota"] else ""
    return _secao("clara borda-topo incluso", f'<div class="caixa caixa-media"><h2>{e(b["titulo"])}</h2>'
                                              f'<div class="ficha"><ul class="lista-check">{itens}</ul>{nota}</div></div>')


def _entrega(b):
    if not b["ativo"]:
        return ""
    cartoes = "".join(f'<div class="cartao cartao-borda"><span class="selo-icone">{_icone(i["icone"])}</span>'
                      f'<h3>{e(i["titulo"])}</h3><p class="desc">{e(i["descricao"])}</p></div>' for i in b["itens"])
    return _secao("branca", f'<div class="caixa caixa-media">{_cabeca(b)}<div class="grade grade-3">{cartoes}</div></div>')


def _bonus(b, mockups=None, tamanhos=None):
    if not b["ativo"]:
        return ""
    cartoes = []
    for n, i in enumerate(b["itens"], 1):
        src = (mockups or {}).get(n, "")
        img = (f'<img class="bonus-mockup" src="{e(src)}" alt="Bônus #{n}: {e(i["titulo"])}" loading="lazy"'
               f'{_tam(src, tamanhos or {})}>' if src else "")
        valor = (f'<p class="valor"><s>{e(i["valor"])}</s> <strong>GRÁTIS</strong></p>' if i["valor"] else "")
        img = f'<div class="vitrine">{img}</div>' if img else ""
        cartoes.append(f'<div class="cartao cartao-vidro cartao-bonus">{img}<p class="rotulo">Bônus #{n}</p><h3>{e(i["titulo"])}</h3>'
                       f'<p class="desc">{e(i["descricao"])}</p>{valor}</div>')
    return _secao("escura", f'<div class="caixa">{_cabeca(b)}<div class="grade grade-2 grade-3l">{"".join(cartoes)}</div></div>')


def _depoimentos(b, imagens, tamanhos=None):
    if not b["ativo"] or not imagens:
        return ""
    fotos = "".join(
        f'<img src="{e(src)}" alt="Depoimento de aluno {i}"{_tam(src, tamanhos or {})} loading="lazy">'
        for i, src in enumerate(imagens, 1))
    return _secao("clara", f'<div class="caixa">{_cabeca(b)}<div class="grade grade-2 grade-3l depoimentos">{fotos}</div></div>')


def _cartao_plano(p, mockup="", tamanhos=None):
    if not p["ativo"]:
        return ""
    foto = (f'<img class="plano-mockup" src="{e(mockup)}" alt="{e(p["nome"])}"{_tam(mockup, tamanhos or {})} '
            'loading="lazy">' if mockup else "")
    selo = '<span class="selo">MAIS VENDIDO</span>' if p["destaque"] else ""
    itens = "".join(f'<li><span class="check" aria-hidden="true">✓</span>{e(i)}</li>' for i in p["itens"])
    de = f'<p class="preco-de">{e(p["precoDe"])}</p>' if p["precoDe"] else ""
    classe = "plano em-destaque" if p["destaque"] else "plano"
    return (f'<div class="{classe}">{selo}{foto}<h3>{e(p["nome"])}</h3><ul>{itens}</ul>'
            f'<div class="precos">{de}<p class="preco-por">{e(p["precoPor"])}</p></div>'
            f'{_cta(p["checkoutUrl"], p["cta"])}</div>')


def _planos(b, mockup="", tamanhos=None):
    if not b["ativo"]:
        return ""
    cartoes = _cartao_plano(b["basico"], mockup, tamanhos) + _cartao_plano(b["premium"])
    ativos = sum(1 for p in (b["basico"], b["premium"]) if p["ativo"])
    grade = "grade grade-2" if ativos > 1 else "grade grade-1"
    return _secao("clara borda-topo planos", f'<div class="caixa caixa-media">{_cabeca(b)}'
                                             f'<div class="{grade}">{cartoes}</div></div>', id_="planos")


def _garantia(b, href):
    if not b["ativo"]:
        return ""
    return _secao("branca", f'<div class="garantia-caixa"><span class="selo-icone">{_icone("escudo")}</span><p class="rotulo">{e(b["titulo"])}</p>'
                            f'<p class="garantia-dias">{b["dias"]} DIAS PARA TESTAR</p>'
                            f'<p class="garantia-texto">{e(b["texto"])}</p>{_cta(href, b["cta"])}</div>')


def _faq(b):
    if not b["ativo"]:
        return ""
    itens = "".join(f'<details><summary>{e(i["pergunta"])}</summary><p>{e(i["resposta"])}</p></details>'
                    for i in b["itens"])
    return _secao("clara", f'<div class="caixa caixa-estreita"><h2>{e(b["titulo"])}</h2><div class="faq">{itens}</div></div>')


def _rodape(b, ano):
    nome = f" {e(b['nomeProduto'])}." if b["nomeProduto"] else ""
    aviso = f'<p class="disclaimer">{e(b["disclaimer"])}</p>' if b["disclaimer"] else ""
    return (f'<footer class="escura rodape"><div class="caixa caixa-estreita"><p>© {ano}{nome} '
            f'Todos os direitos reservados.</p>{aviso}</div></footer>\n')


def _pixels(meta: str, google: str) -> str:
    meta = re.sub(r"[^0-9]", "", meta or "")
    google = re.sub(r"[^A-Za-z0-9-]", "", google or "")
    s = ""
    if meta:
        s += ("<script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?"
              "n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;"
              "n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;"
              "t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,"
              "document,'script','https://connect.facebook.net/en_US/fbevents.js');"
              f"fbq('init','{meta}');fbq('track','PageView');</script>\n"
              '<noscript><img height="1" width="1" style="display:none" '
              f'src="https://www.facebook.com/tr?id={meta}&amp;ev=PageView&amp;noscript=1"></noscript>\n')
    if google:
        s += (f'<script async src="https://www.googletagmanager.com/gtag/js?id={google}"></script>\n'
              "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
              f"gtag('js',new Date());gtag('config','{google}');</script>\n")
    return s


def render_html(conteudo: dict, config: dict, imagens: dict, ano: int) -> str:
    paleta = PALETAS.get(config.get("paleta"), PALETAS[PALETA_PADRAO])
    variaveis = ":root{" + ";".join(f"--pg-{k}:{v}" for k, v in paleta.items()) + "}"
    planos = conteudo["planos"]
    href = "#planos" if planos["ativo"] else (planos["basico"]["checkoutUrl"] or "#")
    hero = conteudo["hero"]
    titulo = (config.get("seo_titulo") or hero["headline"].replace("**", "")
              or conteudo["rodape"]["nomeProduto"] or "Página de vendas")
    descricao = config.get("seo_descricao") or hero["subheadline"]
    tamanhos = imagens.get("tamanhos", {})
    corpo = "".join([
        _hero(hero, imagens.get("logo", ""), href, conteudo["rodape"]["nomeProduto"],
              imagens.get("topo", ""), tamanhos),
        _carrossel(conteudo["carrossel"], imagens.get("carrossel", []), imagens.get("carrossel_mockup", False),
                   tamanhos),
        _para_quem(conteudo["paraQuem"], href),
        _conteudo(conteudo["conteudo"], imagens.get("conteudo", {}), tamanhos),
        _incluso(conteudo["incluso"]),
        _entrega(conteudo["entrega"]),
        _bonus(conteudo["bonus"], imagens.get("bonus", {}), tamanhos),
        _depoimentos(conteudo["depoimentos"], imagens.get("depoimentos", []), tamanhos),
        _planos(planos, imagens.get("topo", ""), tamanhos),
        _garantia(conteudo["garantia"], href),
        _faq(conteudo["faq"]),
        _rodape(conteudo["rodape"], ano),
    ])
    return (
        "<!doctype html>\n<html lang=\"pt-BR\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{e(titulo)}</title>\n"
        f'<meta name="description" content="{e(descricao)}">\n'
        f'<meta property="og:title" content="{e(titulo)}">\n'
        f'<meta property="og:description" content="{e(descricao)}">\n'
        '<meta property="og:type" content="website">\n'
        f"{FONTES}<style>{variaveis}\n{CSS.read_text(encoding='utf-8')}</style>\n"
        f"{_pixels(config.get('pixel_meta', ''), config.get('pixel_google', ''))}"
        f"{config.get('head_html', '')}\n</head>\n<body>\n{corpo}</body>\n</html>\n"
    )


def fotos_da_pasta(pasta: Path) -> list[Path]:
    if not pasta.is_dir():
        return []
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXT_FOTO
                  and not p.name.startswith("."))


def montar_site(pasta_projeto: Path, pasta_pagina: "Path | None" = None) -> "tuple[Path, list[str]]":
    pagina = Path(pasta_pagina) if pasta_pagina else Path(pasta_projeto) / "pagina"
    arq = pagina / "conteudo.json"
    if not arq.exists():
        raise FileNotFoundError(f"Não achei {arq}. Escreva a copy (conteudo.json) antes de montar a página.")
    try:
        bruto = json.loads(arq.read_text(encoding="utf-8"))
    except ValueError as err:
        raise ValueError(f"O {arq} tem um erro de formatação JSON ({err}). Corrija e rode de novo.") from err
    conteudo, avisos = normalizar(bruto)
    config = ler_config(pagina)

    site = pagina / "site"
    novo = pagina / ".site-novo"
    if novo.exists():
        shutil.rmtree(novo)
    (novo / "img").mkdir(parents=True)
    try:
        return _montar(pagina, conteudo, config, avisos, site, novo, _relativa(pasta_projeto, pagina))
    except BaseException:
        shutil.rmtree(novo, ignore_errors=True)
        raise


def _relativa(pasta_projeto, pagina) -> str:
    try:
        return Path(pagina).resolve().relative_to(Path(pasta_projeto).resolve()).as_posix()
    except ValueError:
        return Path(pagina).as_posix()


def _montar(pagina, conteudo, config, avisos, site, novo, rel="pagina"):

    imagens = {"logo": "", "carrossel": [], "depoimentos": [], "topo": "", "bonus": {}, "conteudo": {},
               "tamanhos": {}, "carrossel_mockup": False}
    logos = [p for p in sorted((pagina / "imagens").iterdir())
             if p.is_file() and p.stem.lower() == "logo" and p.suffix.lower() in EXT_LOGO] \
        if (pagina / "imagens").is_dir() else []
    if logos:
        destino = novo / "img" / f"logo{logos[0].suffix.lower()}"
        shutil.copyfile(logos[0], destino)
        imagens["logo"] = f"img/{destino.name}"
        wh = _dimensoes(logos[0])
        if wh:
            imagens["tamanhos"][imagens["logo"]] = wh
    mockups = pagina / "imagens" / "mockups"

    def copiar(origem: Path, nome: str) -> str:
        destino = novo / "img" / nome
        shutil.copyfile(origem, destino)
        src = f"img/{nome}"
        wh = _dimensoes(origem)
        if wh:
            imagens["tamanhos"][src] = wh
        return src

    if conteudo["hero"]["ativo"] and (mockups / "topo.png").is_file():
        imagens["topo"] = copiar(mockups / "topo.png", "mockup-topo.png")
    if conteudo["bonus"]["ativo"]:
        for n in range(1, len(conteudo["bonus"]["itens"]) + 1):
            if (mockups / f"bonus-{n}.png").is_file():
                imagens["bonus"][n] = copiar(mockups / f"bonus-{n}.png", f"mockup-bonus-{n}.png")
    if conteudo["conteudo"]["ativo"]:
        pasta_cards = pagina / "imagens" / "conteudo"
        for n, item in enumerate(conteudo["conteudo"]["itens"], 1):
            propria = pasta_cards / item["imagem"] if item["imagem"] else None
            if propria is not None and propria.is_file():
                imagens["conteudo"][n] = copiar(propria, f"conteudo-{n:02d}{propria.suffix.lower()}")
            elif (mockups / f"conteudo-{n}.png").is_file():
                imagens["conteudo"][n] = copiar(mockups / f"conteudo-{n}.png", f"conteudo-{n:02d}.png")
            if propria is not None and not propria.is_file():
                avisos.append(f'conteudo: não achei {rel}/imagens/conteudo/{item["imagem"]} — o cartão '
                              f'"{item["titulo"]}" ficou sem imagem.')
    brutas = fotos_da_pasta(pagina / "imagens" / "carrossel")
    paginas = sorted(mockups.glob("pagina-[0-9][0-9].png")) if mockups.is_dir() and conteudo["carrossel"]["ativo"] else []
    if paginas:
        imagens["carrossel_mockup"] = True
        for n, foto in enumerate(paginas, 1):
            imagens["carrossel"].append(copiar(foto, f"carrossel-{n:02d}.png"))
        if brutas and max(f.stat().st_mtime for f in brutas) > min(f.stat().st_mtime for f in paginas):
            avisos.append(f"carrossel: as imagens de {rel}/imagens/carrossel/ mudaram depois dos mockups — "
                          "rode o pagina_mockups.py de novo pra atualizar.")
    else:
        for n, foto in enumerate(brutas, 1):
            imagens["carrossel"].append(copiar(foto, f"carrossel-{n:02d}{foto.suffix.lower()}"))
    for n, foto in enumerate(fotos_da_pasta(pagina / "imagens" / "depoimentos"), 1):
        imagens["depoimentos"].append(copiar(foto, f"depoimento-{n:02d}{foto.suffix.lower()}"))
    if not imagens["depoimentos"]:
        avisos.append(f"depoimentos: sem prints em {rel}/imagens/depoimentos/ — a seção fica escondida "
                      "(coloque só depoimentos reais).")
    if conteudo["carrossel"]["ativo"] and not imagens["carrossel"]:
        avisos.append(f"carrossel: sem imagens em {rel}/imagens/carrossel/ — a seção fica escondida.")

    if FONTES_DIR.is_dir():
        (novo / "fontes").mkdir()
        for fonte in FONTES_DIR.glob("*.woff2"):
            shutil.copyfile(fonte, novo / "fontes" / fonte.name)
    index = novo / "index.html"
    index.write_text(render_html(conteudo, config, imagens, date.today().year), encoding="utf-8")
    antigo = pagina / ".site-antigo"
    if antigo.exists():
        if not site.exists():
            antigo.rename(site)  # sobrou de uma queda entre os renames: recupera
        else:
            shutil.rmtree(antigo)
    tinha_antigo = site.exists()
    if tinha_antigo:
        site.rename(antigo)
    try:
        novo.rename(site)
    except BaseException:
        if tinha_antigo:
            try:
                antigo.rename(site)
            except OSError:
                pass
        raise
    if tinha_antigo:
        shutil.rmtree(antigo, ignore_errors=True)
    return site / "index.html", avisos


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Monta a página de vendas do projeto.")
    ap.add_argument("--projeto", required=True)
    ap.add_argument("--pagina", default="")
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    try:
        index, avisos = montar_site(Path(args.projeto), Path(args.pagina) if args.pagina else None)
    except (FileNotFoundError, ValueError) as err:
        print(f"❌ {err}", file=sys.stderr)
        return 1
    except OSError as err:
        _log_tecnico(traceback.format_exc())
        print(f"❌ Não consegui gravar a página na pasta do projeto ({type(err).__name__}). "
              "Confira se a pasta existe e se há espaço no disco.", file=sys.stderr)
        return 1
    except Exception:
        _log_tecnico(traceback.format_exc())
        print("❌ Algo deu errado ao montar a página. Detalhes no log da Máquina (~/.maquina/log).",
              file=sys.stderr)
        return 1
    print(f"✅ Página montada: {index}")
    for aviso in avisos:
        print(f"⚠️ {aviso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
