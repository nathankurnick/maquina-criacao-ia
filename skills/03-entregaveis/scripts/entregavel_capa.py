"""Capa (1240x1754) e mockup 3D (1200x1200) de um entregável, montados em HTML/CSS.

Uso: python entregavel_capa.py --pasta <pasta do entregável> [--paleta nome] [--arte "descrição sem texto"]
Com a chave KIE, --arte gera antes uma arte de fundo (Nano Banana); sem chave, imprime o prompt.
"""
import argparse
import html
import os
import sys
import traceback
from pathlib import Path

_HOME = os.environ.get("MAQUINA_HOME") or os.path.expanduser("~/.maquina")
if _HOME not in sys.path:
    sys.path.append(_HOME)
try:
    from nucleo.chaves import obter_chave
    from nucleo.erros import registrar_log
    from nucleo.kie import KieErro, KieErroPermanente, aguardar, baixar, criar_tarefa
    from nucleo.paletas import PALETA_PADRAO, paleta
    NUCLEO_OK = True
except Exception:  # noqa: BLE001
    NUCLEO_OK = False

    class KieErro(Exception):  # type: ignore[no-redef]
        pass

    class KieErroPermanente(KieErro):  # type: ignore[no-redef]
        pass

from entregavel_pdf import ROTULO_TIPO, ler_meta  # noqa: E402

CSS = Path(__file__).resolve().parent.parent / "template" / "capa.css"
MODELO = "nano-banana-2"


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando incompleto ({message}). Use: entregavel_capa.py --pasta <pasta do entregável> "
              '[--paleta nome] [--arte "descrição visual"]', file=sys.stderr)
        raise SystemExit(1)


def e(t) -> str:
    return html.escape(str(t or ""), quote=True)


def _doc(corpo: str, paleta_nome: str) -> str:
    cores = paleta(paleta_nome)
    variaveis = ":root{" + ";".join(f"--pg-{k}:{v}" for k, v in cores.items()) + "}"
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>{variaveis}\n'
            f"{CSS.read_text(encoding='utf-8')}body{{margin:0;background:transparent}}</style></head>"
            f"<body>{corpo}</body></html>")


def html_capa(meta: dict, paleta_nome: str, arte: str = "") -> str:
    fundo = f'<img class="arte" src="{e(arte)}" alt=""><div class="veu"></div>' if arte else ""
    sub = f'<p class="sub">{e(meta.get("subtitulo"))}</p>' if meta.get("subtitulo") else ""
    autor = f'<p class="autor">{e(meta.get("autor"))}</p>' if meta.get("autor") else ""
    n = len(str(meta.get("titulo") or ""))
    classe = ' class="enorme"' if n > 90 else ' class="longo"' if n > 55 else ""
    return _doc(f'<div class="capa">{fundo}<div class="texto"><div class="faixa"></div>'
                f'<p class="tipo">{e(ROTULO_TIPO.get(meta.get("tipo"), "Ebook"))}</p>'
                f'<h1{classe}>{e(meta.get("titulo"))}</h1>{sub}</div>{autor}</div>', paleta_nome)


def html_mockup(capa_png: str, paleta_nome: str) -> str:
    return _doc(f"<div class=\"cena\"><div class=\"sombra\"></div><div class=\"livro\">"
                f"<div class=\"lombada\"></div>"
                f"<div class=\"frente\" style=\"background-image:url('{e(capa_png)}')\"></div></div></div>",
                paleta_nome)


def _e_imagem(arq: Path) -> bool:
    try:
        cab = Path(arq).read_bytes()[:12]
    except OSError:
        return False
    return (cab.startswith(b"\x89PNG\r\n\x1a\n") or cab.startswith(b"\xff\xd8\xff")
            or (cab[:4] == b"RIFF" and cab[8:12] == b"WEBP"))


def gerar_arte(pasta: Path, prompt: str, chave: str) -> Path:
    tid = criar_tarefa(chave, MODELO, {"prompt": prompt, "aspect_ratio": "2:3", "output_format": "png"})
    resultado = aguardar(chave, tid, intervalo=5, limite=150)
    urls = resultado.get("resultUrls") or []
    if not urls:
        raise KieErro("A KIE terminou mas não devolveu a imagem. Tente de novo.")
    pasta = Path(pasta).resolve()
    destino, tmp = pasta / "arte.png", pasta / ".arte.tmp.png"
    try:
        baixar(urls[0], tmp)
        if not _e_imagem(tmp):
            raise KieErro("A KIE devolveu um arquivo que não é imagem.")
        os.replace(tmp, destino)
    finally:
        tmp.unlink(missing_ok=True)
    return destino


def gerar_capa(pasta: Path, paleta_nome: str) -> dict:
    from playwright.sync_api import sync_playwright

    pasta = Path(pasta).resolve()
    meta = ler_meta(pasta)
    arte = "arte.png" if (pasta / "arte.png").exists() else ""
    tmp_capa, tmp_mock = pasta / ".capa.html", pasta / ".mockup.html"
    novo_capa, novo_mock = pasta / ".capa.novo.png", pasta / ".mockup.novo.png"
    capa, mockup = pasta / "capa.png", pasta / "mockup.png"
    try:
        tmp_capa.write_text(html_capa(meta, paleta_nome, arte), encoding="utf-8")
        tmp_mock.write_text(html_mockup(novo_capa.name, paleta_nome), encoding="utf-8")
        with sync_playwright() as p:
            nav = p.chromium.launch()
            try:
                pg = nav.new_page(viewport={"width": 1240, "height": 1754})
                pg.goto(tmp_capa.as_uri(), wait_until="load")
                pg.screenshot(path=str(novo_capa), clip={"x": 0, "y": 0, "width": 1240, "height": 1754})
                pg2 = nav.new_page(viewport={"width": 1200, "height": 1200})
                pg2.goto(tmp_mock.as_uri(), wait_until="load")
                pg2.screenshot(path=str(novo_mock), omit_background=True,
                               clip={"x": 0, "y": 0, "width": 1200, "height": 1200})
            finally:
                try:
                    nav.close()
                except Exception:
                    pass
        os.replace(novo_capa, capa)
        os.replace(novo_mock, mockup)
    finally:
        for t in (tmp_capa, tmp_mock, novo_capa, novo_mock):
            t.unlink(missing_ok=True)
    return {"capa": capa, "mockup": mockup}


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Gera a capa e o mockup do entregável.")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--paleta", default="")
    ap.add_argument("--arte", default="")
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    if not NUCLEO_OK:
        print("❌ A Máquina não está instalada direito (não achei o núcleo). Rode o instalar.sh de novo.",
              file=sys.stderr)
        return 1
    pasta = Path(args.pasta).resolve()
    try:
        ler_meta(pasta)
        if args.arte:
            aviso = ""
            chave = obter_chave("KIE_API_KEY")
            if not chave:
                aviso = "sem_chave"
            else:
                print("🎨 Gerando a arte da capa na KIE (pode levar 1–2 minutos)…")
                try:
                    gerar_arte(pasta, args.arte, chave)
                except KeyboardInterrupt:
                    raise
                except Exception as err:  # noqa: BLE001 — a arte é opcional, nunca derruba a capa
                    if isinstance(err, KieErroPermanente):
                        aviso = f"A arte não saiu (repetir não adianta: {err})."
                    elif isinstance(err, KieErro):
                        aviso = f"A arte não saiu (tente de novo mais tarde: {err})."
                    else:
                        try:
                            registrar_log(traceback.format_exc())
                        except Exception:
                            pass
                        aviso = "A arte não saiu (erro inesperado; detalhes no log da Máquina)."
            if aviso:
                sobra = ("Usei a arte que já estava na pasta (arte.png)." if (pasta / "arte.png").exists()
                         else "Sigo com o fundo na cor da paleta.")
                if aviso == "sem_chave":
                    print("ℹ️ Sem a chave da KIE não dá pra gerar a arte aqui. " + sobra + "\n"
                          f"   Se quiser uma arte nova, gere em outra ferramenta com este prompt e salve como {pasta / 'arte.png'}:\n"
                          f"   {args.arte}\n   Depois rode este comando de novo.")
                else:
                    print(f"⚠️ {aviso} {sobra}")
        r = gerar_capa(pasta, args.paleta or PALETA_PADRAO)
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
            print("❌ O navegador que monta a capa não está instalado. Rode o instalar.sh de novo.", file=sys.stderr)
        else:
            print("❌ Algo deu errado ao montar a capa. Detalhes no log da Máquina (~/.maquina/log).", file=sys.stderr)
        return 1
    print(f"✅ Capa: {r['capa']}\n✅ Mockup: {r['mockup']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
