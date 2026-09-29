"""Monta os criativos estáticos (1080x1080 e 1080x1920) em HTML/CSS: headline sempre legível,
mockup do produto (Sistema 03) e, com a chave KIE, uma cena de fundo gerada antes.

Uso: python anuncio_criativo.py --projeto <P> [--id X] [--paleta nome] [--gerar-arte]
"""
import argparse
import html
import os
import re
import sys
import traceback
from pathlib import Path

_HOME = os.environ.get("MAQUINA_HOME") or os.path.expanduser("~/.maquina")
if _HOME not in sys.path:
    sys.path.append(_HOME)
try:
    from nucleo.chaves import obter_chave
    from nucleo.erros import registrar_log
    from nucleo.kie import KieErro, KieErroPermanente, gerar_imagem
    from nucleo.paletas import PALETA_PADRAO, PALETAS, paleta
    NUCLEO_OK = True
except Exception:  # noqa: BLE001
    NUCLEO_OK = False

    class KieErro(Exception):  # type: ignore[no-redef]
        pass

    class KieErroPermanente(KieErro):  # type: ignore[no-redef]
        pass

from anuncio_dados import _slug, ler_anuncios, paleta_do_projeto  # noqa: E402

CSS = Path(__file__).resolve().parent.parent / "template" / "criativo.css"
FORMATOS_IMG = {"1x1": (1080, 1080, "1:1"), "9x16": (1080, 1920, "9:16")}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando incompleto ({message}). Use: anuncio_criativo.py --projeto <P> [--id X] "
              "[--paleta nome] [--gerar-arte]", file=sys.stderr)
        raise SystemExit(1)


def _destaque(texto: str) -> str:
    partes = re.split(r"(\*\*[^*]+\*\*)", texto)
    s = "".join(f'<span class="destaque">{html.escape(p[2:-2])}</span>' if p.startswith("**") and p.endswith("**")
                and len(p) > 4 else html.escape(p) for p in partes)
    return s.replace("**", "")


def _classe_tamanho(texto: str) -> str:
    n = len(texto.replace("**", ""))
    return "h-curta" if n <= 30 else ("h-media" if n <= 60 else "h-longa")


def html_criativo(anuncio: dict, formato: str, paleta_nome: str, arte: str = "", produto: str = "") -> str:
    largura, altura, _ = FORMATOS_IMG[formato]
    layout = anuncio["visual"]["layout"]
    cores = paleta(paleta_nome)
    variaveis = ":root{" + ";".join(f"--pg-{k}:{v}" for k, v in cores.items()) + "}"
    fundo = f'<img class="arte" src="{html.escape(arte, quote=True)}" alt="">' if arte else ""
    bloco_produto = (f'<div class="produto"><img src="{html.escape(produto, quote=True)}" alt=""></div>'
                     if produto and layout != "centro" else "")
    headline = anuncio["headline_imagem"]
    texto = (f'<div class="texto"><div class="faixa"></div><p class="headline {_classe_tamanho(headline)}">'
             f"{_destaque(headline)}</p></div>")
    miolo = texto + bloco_produto if layout == "topo" else bloco_produto + texto
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>{variaveis}\n'
            f"{CSS.read_text(encoding='utf-8')}</style></head><body>"
            f'<div class="quadro {layout} f{formato}" style="width:{largura}px;height:{altura}px">'
            f'{fundo}<div class="veu"></div>{miolo}</div></body></html>')


def compor(pasta_projeto: Path, anuncio: dict, paleta_nome: str) -> list[Path]:
    from playwright.sync_api import sync_playwright

    pasta_projeto = Path(pasta_projeto).resolve()
    anuncios = pasta_projeto / "anuncios"
    saida = anuncios / "criativos"
    saida.mkdir(parents=True, exist_ok=True)
    produto = ""
    if anuncio["visual"]["produto"]:
        mock = pasta_projeto / "entregaveis" / anuncio["visual"]["produto"] / "mockup.png"
        produto = mock.as_uri() if mock.exists() else ""
    feitos: list[Path] = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        try:
            for fmt, (largura, altura, _) in FORMATOS_IMG.items():
                arte_arq = anuncios / "artes" / f"arte-{anuncio['id']}-{fmt}.png"
                arte = arte_arq.as_uri() if arte_arq.exists() else ""
                tmp_html = saida / f".{anuncio['id']}-{fmt}.html"
                tmp_img = saida / f".{anuncio['id']}-{fmt}.jpg"
                destino = saida / f"{anuncio['id']}-{fmt}.jpg"
                try:
                    tmp_html.write_text(html_criativo(anuncio, fmt, paleta_nome, arte, produto), encoding="utf-8")
                    pg = nav.new_page(viewport={"width": largura, "height": altura})
                    pg.goto(tmp_html.as_uri(), wait_until="load")
                    pg.screenshot(path=str(tmp_img), type="jpeg", quality=90,
                                  clip={"x": 0, "y": 0, "width": largura, "height": altura})
                    pg.close()
                    os.replace(tmp_img, destino)
                    feitos.append(destino)
                finally:
                    tmp_html.unlink(missing_ok=True)
                    tmp_img.unlink(missing_ok=True)
        finally:
            try:
                nav.close()
            except Exception:
                pass
    return feitos


def _gerar_artes(pasta_projeto: Path, anuncio: dict) -> None:
    artes = pasta_projeto / "anuncios" / "artes"
    prompt = anuncio["visual"]["prompt"]
    if not prompt:
        print("ℹ️ Esse anúncio não tem visual.prompt — sigo com o fundo na cor da paleta.")
        return
    nomes = {fmt: artes / f"arte-{anuncio['id']}-{fmt}.png" for fmt in FORMATOS_IMG}
    faltam = {}
    for fmt, dados in FORMATOS_IMG.items():
        if nomes[fmt].exists():
            print(f"ℹ️ Reaproveitei a arte {nomes[fmt].name} (apague o arquivo pra gerar outra).")
        else:
            faltam[fmt] = dados
    if not faltam:
        return
    chave = obter_chave("KIE_API_KEY")
    if not chave:
        print("ℹ️ Sem a chave da KIE. Gere em outra ferramenta (sem texto na imagem) e salve em:")
        for fmt, (_, _, proporcao) in faltam.items():
            print(f"   {nomes[fmt]}  (proporção {proporcao})")
        print(f"   Prompt: {prompt}\n   Depois rode de novo sem --gerar-arte "
              "(as imagens já saíram com o fundo da paleta).")
        return
    artes.mkdir(parents=True, exist_ok=True)
    for fmt, (_, _, proporcao) in faltam.items():
        print(f"🎨 Gerando a cena {proporcao} na KIE (até ~2 minutos)…")
        try:
            gerar_imagem(chave, prompt, proporcao, nomes[fmt])
        except KieErroPermanente as err:
            print(f"⚠️ A arte {proporcao} não saiu (repetir não adianta: {err}).")
        except KieErro as err:
            print(f"⚠️ A arte {proporcao} não saiu (tente de novo mais tarde: {err}).")
        except Exception:  # noqa: BLE001 — arte é opcional
            try:
                registrar_log(traceback.format_exc())
            except Exception:
                pass
            print(f"⚠️ A arte {proporcao} não saiu (erro inesperado).")


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Monta os criativos estáticos.")
    ap.add_argument("--projeto", required=True)
    ap.add_argument("--id", default="")
    ap.add_argument("--paleta", default="")
    ap.add_argument("--gerar-arte", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    if not NUCLEO_OK:
        print("❌ A Máquina não está instalada direito (não achei o núcleo). Rode o instalar.sh de novo.",
              file=sys.stderr)
        return 1
    projeto = Path(args.projeto).resolve()
    try:
        anuncios = ler_anuncios(projeto / "anuncios")
        if args.gerar_arte and not args.id:
            raise ValueError("Gere a arte um anúncio por vez: use --id <id> junto com --gerar-arte.")
        if args.paleta and args.paleta not in PALETAS:
            raise ValueError(f'Paleta "{args.paleta}" não existe. Use uma destas: {", ".join(PALETAS)}.')
        if args.id:
            id_slug = _slug(args.id)
            escolhidos = [a for a in anuncios if a["id"] == id_slug]
            if not escolhidos:
                raise ValueError(f'Não achei o anúncio "{args.id}" no anuncios.json.')
            if escolhidos[0]["formato"] != "estatico":
                raise ValueError(f'"{args.id}" é vídeo — criativo de imagem só pra anúncio estático.')
        else:
            escolhidos = [a for a in anuncios if a["formato"] == "estatico"]
        if not escolhidos:
            print("Nenhum anúncio estático no anuncios.json.")
            return 0
        nome_paleta = args.paleta or paleta_do_projeto(projeto) or PALETA_PADRAO
        for a in escolhidos:
            if args.gerar_arte:
                _gerar_artes(projeto, a)
            produto = a["visual"]["produto"]
            if produto and a["visual"]["layout"] != "centro" and not (projeto / "entregaveis" / produto / "mockup.png").exists():
                print(f"⚠️ {a['id']}: não achei o mockup de '{produto}' (rode a capa no Sistema 03). Sigo sem produto.")
            for arq in compor(projeto, a, nome_paleta):
                print(f"✅ {arq}")
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
            print("❌ O navegador que monta os criativos não está instalado. Rode o instalar.sh de novo.",
                  file=sys.stderr)
        else:
            print("❌ Algo deu errado ao montar os criativos. Detalhes no log da Máquina (~/.maquina/log).",
                  file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
