# skills/02-pagina-de-vendas/scripts/pagina_render.py
"""Monta o site estático da página de vendas (template do Gerador) na pasta do aluno.

Uso: python pagina_render.py --projeto <pasta do projeto>
Lê <P>/pagina/conteudo.json, config.json e imagens/; recria <P>/pagina/site/.
"""
import argparse
import html
import json
import os
import re
import shutil
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


def _icone(nome: str) -> str:
    caminhos = "".join(f'<path d="{d}"/>' for d in ICONES.get(nome, ICONES["estrela"]))
    return ('<svg class="icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
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


def _hero(b, logo, href, nome=""):
    if not b["ativo"]:
        return ""
    partes = []
    if logo:
        partes.append(f'<img class="logo" src="{e(logo)}" alt="{e(nome)}">')
    if b["badge"]:
        partes.append(f'<p class="badge">{e(b["badge"])}</p>')
    partes.append(f"<h1>{com_destaque(b['headline'])}</h1>")
    if b["subheadline"]:
        partes.append(f'<p class="subheadline">{e(b["subheadline"])}</p>')
    partes.append(_cta(href, b["cta"]))
    return _secao("escura hero", f'<div class="caixa caixa-estreita centro">{"".join(partes)}</div>')


def _carrossel(b, imagens):
    if not b["ativo"] or not imagens:
        return ""
    fotos = "".join(f'<img src="{e(src)}" alt="Imagem {i} do material">' for i, src in enumerate(imagens, 1))
    desc = f'<p class="sub">{e(b["descricao"])}</p>' if b["descricao"] else ""
    return _secao("clara borda-topo",
                  f'<div class="caixa"><h2>{e(b["titulo"])}</h2>{desc}<div class="carrossel">{fotos}</div></div>')


def _para_quem(b, href):
    if not b["ativo"]:
        return ""
    cartoes = "".join(f'<div class="cartao cartao-claro"><h3>{e(i["titulo"])}</h3>'
                      f'<p class="desc">{e(i["descricao"])}</p></div>' for i in b["itens"])
    return _secao("branca", f'<div class="caixa">{_cabeca(b)}<div class="grade grade-3">{cartoes}</div>'
                            f'<div class="centro">{_cta(href, "QUERO ACESSAR AGORA")}</div></div>')


def _conteudo(b):
    if not b["ativo"]:
        return ""
    cartoes = "".join(f'<div class="cartao cartao-vidro">{_icone(i["icone"])}<h3>{e(i["titulo"])}</h3>'
                      f'<p class="desc">{e(i["descricao"])}</p></div>' for i in b["itens"])
    return _secao("media", f'<div class="caixa">{_cabeca(b)}<div class="grade grade-2 grade-3l">{cartoes}</div></div>')


def _incluso(b):
    if not b["ativo"]:
        return ""
    itens = "".join(f'<li><span class="check" aria-hidden="true">✓</span><div><p class="item-titulo">'
                    f'{e(i["titulo"])}</p><p class="desc">{e(i["descricao"])}</p></div></li>' for i in b["itens"])
    nota = f'<p class="nota">{e(b["nota"])}</p>' if b["nota"] else ""
    return _secao("clara borda-topo", f'<div class="caixa caixa-media"><h2>{e(b["titulo"])}</h2>'
                                      f'<ul class="lista-check">{itens}</ul>{nota}</div>')


def _entrega(b):
    if not b["ativo"]:
        return ""
    cartoes = "".join(f'<div class="cartao cartao-borda"><h3>{e(i["titulo"])}</h3>'
                      f'<p class="desc">{e(i["descricao"])}</p></div>' for i in b["itens"])
    return _secao("branca", f'<div class="caixa caixa-media">{_cabeca(b)}<div class="grade grade-3">{cartoes}</div></div>')


def _bonus(b):
    if not b["ativo"]:
        return ""
    cartoes = []
    for n, i in enumerate(b["itens"], 1):
        valor = (f'<p class="valor"><s>{e(i["valor"])}</s> <strong>GRÁTIS</strong></p>' if i["valor"] else "")
        cartoes.append(f'<div class="cartao cartao-vidro"><p class="rotulo">Bônus #{n}</p><h3>{e(i["titulo"])}</h3>'
                       f'<p class="desc">{e(i["descricao"])}</p>{valor}</div>')
    return _secao("escura", f'<div class="caixa">{_cabeca(b)}<div class="grade grade-2 grade-3l">{"".join(cartoes)}</div></div>')


def _depoimentos(b, imagens):
    if not b["ativo"] or not imagens:
        return ""
    fotos = "".join(f'<img src="{e(src)}" alt="Depoimento de aluno {i}">' for i, src in enumerate(imagens, 1))
    return _secao("clara", f'<div class="caixa">{_cabeca(b)}<div class="grade grade-2 grade-3l depoimentos">{fotos}</div></div>')


def _cartao_plano(p):
    if not p["ativo"]:
        return ""
    selo = '<span class="selo">MAIS VENDIDO</span>' if p["destaque"] else ""
    itens = "".join(f'<li><span class="check" aria-hidden="true">✓</span>{e(i)}</li>' for i in p["itens"])
    de = f'<p class="preco-de">{e(p["precoDe"])}</p>' if p["precoDe"] else ""
    classe = "plano em-destaque" if p["destaque"] else "plano"
    return (f'<div class="{classe}">{selo}<h3>{e(p["nome"])}</h3><ul>{itens}</ul>'
            f'<div class="precos">{de}<p class="preco-por">{e(p["precoPor"])}</p></div>'
            f'{_cta(p["checkoutUrl"], p["cta"])}</div>')


def _planos(b):
    if not b["ativo"]:
        return ""
    cartoes = _cartao_plano(b["basico"]) + _cartao_plano(b["premium"])
    return _secao("clara borda-topo planos", f'<div class="caixa caixa-media">{_cabeca(b)}'
                                             f'<div class="grade grade-2">{cartoes}</div></div>', id_="planos")


def _garantia(b, href):
    if not b["ativo"]:
        return ""
    return _secao("branca", f'<div class="garantia-caixa"><p class="rotulo">{e(b["titulo"])}</p>'
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
    return (f'<footer class="escura rodape"><div class="caixa caixa-estreita"><p>© {ano}{nome} '
            f'Todos os direitos reservados.</p><p class="disclaimer">{e(b["disclaimer"])}</p></div></footer>\n')


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
    corpo = "".join([
        _hero(hero, imagens.get("logo", ""), href, conteudo["rodape"]["nomeProduto"]),
        _carrossel(conteudo["carrossel"], imagens.get("carrossel", [])),
        _para_quem(conteudo["paraQuem"], href),
        _conteudo(conteudo["conteudo"]),
        _incluso(conteudo["incluso"]),
        _entrega(conteudo["entrega"]),
        _bonus(conteudo["bonus"]),
        _depoimentos(conteudo["depoimentos"], imagens.get("depoimentos", [])),
        _planos(planos),
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
        f"<style>{variaveis}\n{CSS.read_text(encoding='utf-8')}</style>\n"
        f"{_pixels(config.get('pixel_meta', ''), config.get('pixel_google', ''))}"
        f"{config.get('head_html', '')}\n</head>\n<body>\n{corpo}</body>\n</html>\n"
    )


def _fotos(pasta: Path) -> list[Path]:
    if not pasta.is_dir():
        return []
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXT_FOTO
                  and not p.name.startswith("."))


def montar_site(pasta_projeto: Path) -> "tuple[Path, list[str]]":
    pagina = Path(pasta_projeto) / "pagina"
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
        return _montar(pagina, conteudo, config, avisos, site, novo)
    except BaseException:
        shutil.rmtree(novo, ignore_errors=True)
        raise


def _montar(pagina, conteudo, config, avisos, site, novo):

    imagens = {"logo": "", "carrossel": [], "depoimentos": []}
    logos = [p for p in sorted((pagina / "imagens").iterdir())
             if p.is_file() and p.stem.lower() == "logo" and p.suffix.lower() in EXT_LOGO] \
        if (pagina / "imagens").is_dir() else []
    if logos:
        destino = novo / "img" / f"logo{logos[0].suffix.lower()}"
        shutil.copyfile(logos[0], destino)
        imagens["logo"] = f"img/{destino.name}"
    for tipo, prefixo in (("carrossel", "carrossel"), ("depoimentos", "depoimento")):
        for n, foto in enumerate(_fotos(pagina / "imagens" / tipo), 1):
            destino = novo / "img" / f"{prefixo}-{n:02d}{foto.suffix.lower()}"
            shutil.copyfile(foto, destino)
            imagens[tipo].append(f"img/{destino.name}")
    if not imagens["depoimentos"]:
        avisos.append("depoimentos: sem prints em pagina/imagens/depoimentos/ — a seção fica escondida "
                      "(coloque só depoimentos reais).")
    if conteudo["carrossel"]["ativo"] and not imagens["carrossel"]:
        avisos.append("carrossel: sem imagens em pagina/imagens/carrossel/ — a seção fica escondida.")

    index = novo / "index.html"
    index.write_text(render_html(conteudo, config, imagens, date.today().year), encoding="utf-8")
    if site.exists():
        shutil.rmtree(site)
    novo.rename(site)
    return site / "index.html", avisos


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Monta a página de vendas do projeto.")
    ap.add_argument("--projeto", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    try:
        index, avisos = montar_site(Path(args.projeto))
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
