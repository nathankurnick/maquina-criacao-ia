# skills/03-entregaveis/scripts/entregavel_pdf.py
"""Gera o PDF diagramado de um entregável (A4 ou slides 16:9) + amostras pro carrossel da página.

Uso: python entregavel_pdf.py --pasta <P>/entregaveis/<slug> [--paleta nome] [--carrossel <pasta>] [--ordem 1-99]
Lê meta.json + conteudo.md (+ capa.png se existir) e grava <slug>.pdf e previa/amostra-N.png.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
import traceback
from pathlib import Path

_HOME = os.environ.get("MAQUINA_HOME") or os.path.expanduser("~/.maquina")
if _HOME not in sys.path:
    sys.path.append(_HOME)
try:
    from nucleo.erros import registrar_log
    from nucleo.paletas import PALETA_PADRAO, paleta
    NUCLEO_OK = True
except Exception:  # noqa: BLE001 — sem núcleo, main() avisa
    NUCLEO_OK = False

from entregavel_md import converter, dividir_slides  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent.parent / "template"
TIPOS_DOCUMENTO = ("ebook", "guia", "checklist", "roteiro")
TIPOS = TIPOS_DOCUMENTO + ("slides",)
ROTULO_TIPO = {"ebook": "Ebook", "guia": "Guia prático", "checklist": "Checklist",
               "roteiro": "Roteiro de aulas", "slides": "Slides"}
RODAPE = ('<div style="width:100%;text-align:center;font-size:9px;color:#888;">'
          '<span class="pageNumber"></span></div>')
A4_W, A4_H = 794, 1123


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando incompleto ({message}). Use: entregavel_pdf.py --pasta <pasta do entregável> "
              "[--paleta nome] [--carrossel <pasta>] [--ordem 1-99]", file=sys.stderr)
        raise SystemExit(1)


def e(t) -> str:
    return html.escape(str(t or ""), quote=True)


def ler_meta(pasta: Path) -> dict:
    arq = Path(pasta) / "meta.json"
    try:
        bruto = json.loads(arq.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ValueError(f"Não achei {arq}. Crie o meta.json do entregável (titulo, tipo…).") from err
    except UnicodeDecodeError as err:
        raise ValueError(f"O {arq} não está em UTF-8. Abra e salve o arquivo como UTF-8.") from err
    except (OSError, ValueError) as err:
        raise ValueError(f"O {arq} tem um erro de formatação ({type(err).__name__}). Corrija e rode de novo.") from err
    if not isinstance(bruto, dict) or not str(bruto.get("titulo") or "").strip():
        raise ValueError(f"O {arq} precisa ter o campo titulo.")
    tipo = str(bruto.get("tipo") or "ebook").strip().lower()
    if tipo not in TIPOS:
        raise ValueError(f'tipo "{tipo}" não existe no {arq}. Use: {", ".join(TIPOS)}.')
    return {"titulo": str(bruto["titulo"]).strip(), "subtitulo": str(bruto.get("subtitulo") or "").strip(),
            "tipo": tipo, "autor": str(bruto.get("autor") or "").strip()}


def _variaveis(paleta_nome: str) -> str:
    cores = paleta(paleta_nome)
    return ":root{" + ";".join(f"--pg-{k}:{v}" for k, v in cores.items()) + "}"


def _documento(meta: dict, markdown: str, capa_img: str) -> str:
    corpo, titulos = converter(markdown)
    if capa_img:
        capa = f'<section class="capa"><img class="capa-imagem" src="{e(capa_img)}" alt=""></section>'
    else:
        sub = f'<p class="capa-subtitulo">{e(meta["subtitulo"])}</p>' if meta["subtitulo"] else ""
        autor = f'<p class="capa-autor">{e(meta["autor"])}</p>' if meta["autor"] else ""
        capa = (f'<section class="capa"><div class="faixa"></div><p class="tipo">{e(ROTULO_TIPO[meta["tipo"]])}</p>'
                f'<h1 class="capa-titulo">{e(meta["titulo"])}</h1>{sub}{autor}</section>')
    itens = "".join(f'<li class="n{t["nivel"]}"><a href="#{t["id"]}">{e(t["texto"])}</a></li>' for t in titulos)
    sumario = f'<section class="sumario"><h2>Sumário</h2><ol>{itens}</ol></section>' if titulos else ""
    partes = re.split(r"(?=<h1[ >])", corpo)
    corpo = partes[0] + "".join(f'<section class="capitulo">{c}</section>' for c in partes[1:])
    return f"{capa}{sumario}<main>{corpo}</main>"


def _slides(meta: dict, markdown: str) -> str:
    sub = f'<p class="subtitulo">{e(meta["subtitulo"])}</p>' if meta["subtitulo"] else ""
    partes = [f'<section class="slide titulo"><h1>{e(meta["titulo"])}</h1>{sub}</section>']
    for bloco in dividir_slides(markdown):
        corpo, _ = converter(bloco)
        partes.append(f'<section class="slide">{corpo}</section>')
    return "".join(partes)


def montar_html(meta: dict, markdown: str, paleta_nome: str, capa_img: str = "") -> str:
    slides = meta["tipo"] == "slides"
    css = (TEMPLATE / ("slides.css" if slides else "documento.css")).read_text(encoding="utf-8")
    corpo = _slides(meta, markdown) if slides else _documento(meta, markdown, capa_img)
    return ("<!doctype html>\n<html lang=\"pt-BR\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<title>{e(meta['titulo'])}</title>\n<style>{_variaveis(paleta_nome)}\n{css}</style>\n"
            f"</head>\n<body>\n{corpo}\n</body>\n</html>\n")


def _salvar_pdf(pg, opcoes: dict) -> None:
    pg.pdf(**opcoes)


_JS_CANDIDATOS = """() => {
  const topo = el => el.getBoundingClientRect().top + window.scrollY;
  const caps = [...document.querySelectorAll('.capitulo')].map((el, i) => {
    const t0 = topo(el);
    const dentro = v => topo(v) - t0 < %(alto)d;
    const imagens = [...el.querySelectorAll('img')].filter(dentro).length;
    const outros = [...el.querySelectorAll('.caixa, table, .checklist')].filter(dentro).length;
    return {i, y: t0, pontos: imagens * 10 + outros};
  });
  const s = document.querySelector('.sumario');
  const m = document.querySelector('main');
  return {caps, sumario: s ? {y: topo(s), itens: s.querySelectorAll('li').length} : null,
          main: m ? topo(m) : 0};
}"""


def escolher_alvos(cand: dict) -> list:
    """Devolve [(alvo, y)] das 2 páginas mais visuais (imagem > tabela/caixa/checklist). Nunca o
    sumário: ele não vende. Com menos de 2 capítulos, recorta o <main> a partir do 1º capítulo."""
    caps = sorted(cand["caps"], key=lambda c: (-c["pontos"], c["i"]))
    alvos = [("capitulo", c["y"]) for c in caps][:2]
    if len(alvos) < 2:
        return [("main", cand["main"]), ("main", cand["main"] + A4_H)]
    return alvos


def _capa_antiga(pasta: Path) -> bool:
    capa, meta = pasta / "capa.png", pasta / "meta.json"
    return capa.exists() and meta.exists() and meta.stat().st_mtime > capa.stat().st_mtime


def gerar(pasta: Path, paleta_nome: str, carrossel: "Path | None" = None, ordem: int = 50) -> dict:
    from playwright.sync_api import sync_playwright

    pasta = Path(pasta).resolve()
    meta = ler_meta(pasta)
    md_arq = pasta / "conteudo.md"
    if not md_arq.exists():
        raise ValueError(f"Não achei {md_arq}. Escreva o conteúdo do entregável antes de gerar o PDF.")
    slides = meta["tipo"] == "slides"
    capa = "capa.png" if (pasta / "capa.png").exists() and not slides else ""
    try:
        markdown = md_arq.read_text(encoding="utf-8")
    except UnicodeDecodeError as err:
        raise ValueError(f"O {md_arq} não está em UTF-8. Abra e salve o arquivo como UTF-8.") from err
    avisos: list[str] = []
    if capa and _capa_antiga(pasta):
        avisos.append("⚠️ A capa (capa.png) é mais antiga que o meta.json — se mudou título, subtítulo ou autor, "
                      "rode a capa de novo (sem --arte) antes do PDF.")
    if carrossel is not None and meta["tipo"] == "roteiro":
        carrossel = None
        avisos.append("ℹ️ Roteiro é material interno do curso: não copiei imagens pro carrossel da página.")
    documento = montar_html(meta, markdown, paleta_nome, capa)
    render = pasta / ".render.html"
    render.write_text(documento, encoding="utf-8")
    pdf = pasta / f"{pasta.name}.pdf"
    pdf_tmp = pasta / ".render.pdf"
    previa = pasta / "previa"
    previa.mkdir(exist_ok=True)
    amostras: list[Path] = []
    novas: list[Path] = []
    clips: list[dict] = []
    try:
        with sync_playwright() as p:
            nav = p.chromium.launch()
            try:
                if slides:
                    pg = nav.new_page(viewport={"width": 1280, "height": 720})
                else:
                    pg = nav.new_page(viewport={"width": A4_W, "height": A4_H})
                pg.goto(render.as_uri(), wait_until="load")
                pg.emulate_media(media="print")
                opcoes = {"path": str(pdf_tmp), "print_background": True, "prefer_css_page_size": True}
                if not slides:
                    opcoes.update(display_header_footer=True, header_template="<span></span>",
                                  footer_template=RODAPE)
                _salvar_pdf(pg, opcoes)
                pg.emulate_media(media="screen")
                if slides:
                    alvos = []
                    for el in pg.query_selector_all(".slide")[1:3]:
                        alvos.append(("slide", el.bounding_box()["y"] + pg.evaluate("window.scrollY")))
                    largura, alto = 1280, 720
                else:
                    # cada bloco vira uma "página" A4 com as margens do @page
                    pg.add_style_tag(content=(
                        ".sumario,.capitulo{width:794px;min-height:1123px;padding:18mm 16mm 20mm;"
                        "background:#fff;break-before:auto;break-after:auto}.capitulo h1{break-before:auto}"
                        "main{display:block}"))
                    largura, alto = A4_W, A4_H
                    cand = pg.evaluate(_JS_CANDIDATOS % {"alto": A4_H})
                    alvos = escolher_alvos(cand)
                    if alvos[0][0] == "main":  # o <main> vira a "página": sem o padding duplo dos capítulos
                        # 2 páginas A4 + folga (>= padding-topo de 18mm ~ 68px) pro 2º recorte nunca passar do fim
                        pg.add_style_tag(content=(f"main{{padding:18mm 16mm 20mm;min-height:{2 * A4_H + 200}px}}"
                                                  ".capitulo{padding:0;min-height:0}"))
                        alvos = [("main", pg.evaluate("(document.querySelector('.capitulo') || document.querySelector('main'))"
                                                      ".getBoundingClientRect().top + window.scrollY") + k * A4_H)
                                 for k in (0, 1)]
                for k, (alvo, y) in enumerate(alvos, 1):
                    destino = previa / f".amostra-{k}.png"
                    novas.append(destino)
                    pg.screenshot(path=str(destino), full_page=True,
                                  clip={"x": 0, "y": y, "width": largura, "height": alto})
                    clips.append({"alvo": alvo, "y": y})
            finally:
                try:
                    nav.close()
                except Exception:
                    pass
        # render ok: agora sim troca as amostras antigas pelas novas
        for velho in previa.glob("amostra-*.png"):
            velho.unlink()
        for k, tmp in enumerate(novas, 1):
            destino = previa / f"amostra-{k}.png"
            tmp.replace(destino)
            amostras.append(destino)
    except BaseException:
        pdf_tmp.unlink(missing_ok=True)
        for tmp in novas:
            tmp.unlink(missing_ok=True)
        raise
    else:
        pdf_tmp.replace(pdf)
    finally:
        render.unlink(missing_ok=True)

    copiados: list[Path] = []
    if carrossel is not None:
        carrossel = Path(carrossel)
        carrossel.mkdir(parents=True, exist_ok=True)
        padrao = re.compile(rf"(\d{{2}}-)?{re.escape(pasta.name)}-\d{{2}}\.(png|jpg)")
        for velho in carrossel.iterdir():
            if padrao.fullmatch(velho.name):
                velho.unlink()
        prefixo = f"{ordem:02d}-{pasta.name}"
        origens = list(amostras)
        for n, origem in enumerate(origens, 1):
            destino = carrossel / f"{prefixo}-{n:02d}{origem.suffix}"
            shutil.copyfile(origem, destino)
            copiados.append(destino)
    return {"pdf": pdf, "amostras": amostras, "carrossel": copiados, "clips": clips, "avisos": avisos}


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Gera o PDF de um entregável.")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--paleta", default="")
    ap.add_argument("--carrossel", default="")
    ap.add_argument("--ordem", default="50")
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    if not re.fullmatch(r"\d{1,2}", args.ordem.strip()) or not 1 <= int(args.ordem) <= 99:
        print("❌ O --ordem precisa ser um número de 1 a 99 (ex.: --ordem 1 para o produto principal).",
              file=sys.stderr)
        return 1
    args.ordem = int(args.ordem)
    if not NUCLEO_OK:
        print("❌ A Máquina não está instalada direito (não achei o núcleo). Rode o instalar.sh de novo.",
              file=sys.stderr)
        return 1
    try:
        print("📄 Gerando o PDF…")
        r = gerar(Path(args.pasta), args.paleta or PALETA_PADRAO,
                  Path(args.carrossel) if args.carrossel else None, args.ordem)
    except KeyboardInterrupt:
        print("Cancelado.", file=sys.stderr)
        return 130
    except ValueError as err:
        print(f"❌ {err}", file=sys.stderr)
        return 1
    except Exception as err:
        try:
            registrar_log(traceback.format_exc())
        except Exception:
            pass
        if "Executable doesn't exist" in str(err) or isinstance(err, ImportError):
            print("❌ O navegador que gera o PDF não está instalado. Rode o instalar.sh de novo.", file=sys.stderr)
        else:
            print("❌ Algo deu errado ao gerar o PDF. Detalhes no log da Máquina (~/.maquina/log).", file=sys.stderr)
        return 1
    for aviso in r["avisos"]:
        print(aviso)
    print(f"✅ PDF pronto: {r['pdf']}")
    for a in r["amostras"]:
        print(f"   Amostra: {a}")
    if r["carrossel"]:
        print(f"   {len(r['carrossel'])} imagem(ns) no carrossel da página — rode o Sistema 02 de novo pra aparecer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
