# skills/05-funil/scripts/funil_oto.py
"""Página de upsell/downsell no formato do método Segredos do Upsell (OTO): pré-headline,
headline, vídeo sem autoplay (ou texto), copy abaixo, botão com atraso e "não, obrigado".

Uso: python funil_oto.py --pasta <P>/funil/upsell [--paleta nome] [--publicar]
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
    from nucleo.chaves import obter_chave
    from nucleo.erros import MaquinaErro, registrar_log
    from nucleo.netlify import publicar_pasta
    from nucleo.paletas import PALETA_PADRAO, PALETAS, paleta
    NUCLEO_OK = True
except Exception:  # noqa: BLE001
    NUCLEO_OK = False

    class MaquinaErro(Exception):  # type: ignore[no-redef]
        pass

CSS = Path(__file__).resolve().parent.parent / "template" / "oto.css"
PADROES = {
    "pre_headline": "⚠️ Não feche esta página e não clique em voltar — isso pode gerar erros no seu pedido.",
    "headline": "Seu pedido foi aprovado, mas ainda não foi concluído. Veja a mensagem abaixo.",
    "copy_abaixo": "Faça isso agora: assista à mensagem acima até o final. Seu link de acesso aparece em seguida.",
    "botao_texto": "SIM, QUERO ADICIONAR AO MEU PEDIDO",
    "recusar_texto": "Não, obrigado. Quero seguir só com o que já comprei.",
}


class SemToken(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print("❌ Comando incompleto (falta --pasta ou valor inválido). Use: funil_oto.py --pasta <P>/funil/upsell "
              "[--paleta nome] [--publicar]", file=sys.stderr)
        raise SystemExit(1)


def e(t) -> str:
    return html.escape(str(t or ""), quote=True)


def checkout_valido(url: str) -> bool:
    return bool(re.fullmatch(r"https://[^\s/]+\.[^\s]+", url or "")) and "seu-link" not in url.lower()


def embed_video(v: str) -> str:
    v = (v or "").strip()
    if v.startswith("<"):
        return f'<div class="video">{v}</div>'
    m = (re.search(r"youtube\.com/watch\?(?:.*&)?v=([\w-]{6,})", v) or re.search(r"youtu\.be/([\w-]{6,})", v)
         or re.search(r"youtube\.com/shorts/([\w-]{6,})", v))
    if m:
        src = f"https://www.youtube-nocookie.com/embed/{m.group(1)}?rel=0"
    else:
        m = re.search(r"vimeo\.com/(\d+)", v)
        if not m:
            raise ValueError("o vídeo precisa ser um link do YouTube/Vimeo ou o código de incorporação do player "
                             "(VTurb, Panda…)")
        src = f"https://player.vimeo.com/video/{m.group(1)}"
    return (f'<div class="video iframe"><iframe src="{e(src)}" title="Mensagem" '
            'allow="encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe></div>')


def _txt(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def ler_oto(pasta: Path) -> dict:
    arq = Path(pasta) / "oto.json"
    try:
        bruto = json.loads(arq.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ValueError(f"Não achei {arq}. Escreva o conteúdo da página antes.") from err
    except UnicodeDecodeError as err:
        raise ValueError(f"O {arq} não está em UTF-8. Salve como UTF-8.") from err
    except (OSError, ValueError) as err:
        raise ValueError(f"O {arq} tem um erro de formatação ({type(err).__name__}).") from err
    if not isinstance(bruto, dict):
        raise ValueError(f"O {arq} precisa ser um objeto.")
    oto = {k: _txt(bruto.get(k)) or padrao for k, padrao in PADROES.items()}
    oto["formato"] = _txt(bruto.get("formato")) or "video"
    if oto["formato"] not in ("video", "texto"):
        raise ValueError('formato precisa ser "video" ou "texto".')
    oto["video"], oto["texto"] = _txt(bruto.get("video")), _txt(bruto.get("texto"))
    if oto["formato"] == "video":
        embed_video(oto["video"])
    elif not oto["texto"]:
        raise ValueError('no formato "texto", escreva a copy no campo texto.')
    oto["botao_html"] = _txt(bruto.get("botao_html"))
    oto["checkout_url"] = _txt(bruto.get("checkout_url"))
    if not oto["botao_html"] and not checkout_valido(oto["checkout_url"]):
        raise ValueError("checkout_url precisa ser o link real de pagamento do upsell (https://…), "
                         "ou cole o código do botão de 1 clique em botao_html.")
    atraso = bruto.get("atraso_segundos", 0)
    if isinstance(atraso, bool) or not isinstance(atraso, int) or atraso < 0:
        raise ValueError("atraso_segundos precisa ser um número inteiro de segundos (0 ou mais).")
    oto["atraso_segundos"] = atraso
    oto["recusar_url"] = _txt(bruto.get("recusar_url"))
    if oto["recusar_url"] and not checkout_valido(oto["recusar_url"]):
        raise ValueError("recusar_url precisa ser um endereço https:// (a próxima página: downsell ou obrigado).")
    return oto


def html_oto(oto: dict, paleta_nome: str) -> str:
    cores = paleta(paleta_nome)
    variaveis = ":root{" + ";".join(f"--pg-{k}:{v}" for k, v in cores.items()) + "}"
    if oto["formato"] == "video":
        miolo = embed_video(oto["video"])
    else:
        paragrafos = "".join(f"<p>{e(p.strip())}</p>" for p in re.split(r"\n\s*\n", oto["texto"]) if p.strip())
        miolo = f'<div class="texto">{paragrafos}</div>'
    botao = oto["botao_html"] or f'<a class="botao" href="{e(oto["checkout_url"])}">{e(oto["botao_texto"])}</a>'
    recusar = (f'<br><a class="recusar" href="{e(oto["recusar_url"])}">{e(oto["recusar_texto"])}</a>'
               if oto["recusar_url"] else "")
    classe = "oferta escondida" if oto["atraso_segundos"] > 0 else "oferta"
    script = ("<script>setTimeout(function(){var o=document.querySelector('.oferta');"
              f"if(o){{o.classList.remove('escondida');}}}},{oto['atraso_segundos'] * 1000});</script>"
              if oto["atraso_segundos"] > 0 else "")
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="robots" content="noindex"><title>{e(oto["headline"])}</title>'
            f"<style>{variaveis}\n{CSS.read_text(encoding='utf-8')}</style></head><body>"
            f'<p class="aviso">{e(oto["pre_headline"])}</p><div class="caixa"><h1>{e(oto["headline"])}</h1>'
            f'{miolo}<p class="abaixo">{e(oto["copy_abaixo"])}</p><div class="{classe}">{botao}{recusar}</div>'
            f"</div>{script}</body></html>\n")


def montar(pasta: Path, paleta_nome: str) -> Path:
    pasta = Path(pasta).resolve()
    documento = html_oto(ler_oto(pasta), paleta_nome)
    site, novo, antigo = pasta / "site", pasta / ".site-novo", pasta / ".site-antigo"
    if antigo.exists() and not site.exists():
        antigo.rename(site)
    for velho in (novo, antigo):
        if velho.exists():
            shutil.rmtree(velho)
    novo.mkdir()
    try:
        (novo / "index.html").write_text(documento, encoding="utf-8")
        if site.exists():
            site.rename(antigo)
        try:
            novo.rename(site)
        except BaseException:
            if antigo.exists() and not site.exists():
                antigo.rename(site)
            raise
        if antigo.exists():
            shutil.rmtree(antigo)
    finally:
        if novo.exists():
            shutil.rmtree(novo)
    return site / "index.html"


def _config(pasta: Path) -> dict:
    try:
        dados = json.loads((pasta / "config.json").read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def publicar(pasta: Path) -> dict:
    pasta = Path(pasta).resolve()
    site = pasta / "site"
    if not (site / "index.html").exists():
        raise MaquinaErro("A página ainda não foi montada.")
    token = obter_chave("NETLIFY_TOKEN")
    if not token:
        raise SemToken()
    config = _config(pasta)
    anterior = config.get("url", "")
    r = publicar_pasta(token, site, config.get("site_id") or None)
    config.update(site_id=r["site_id"], url=r["url"])
    tmp = pasta / ".config.json.tmp"
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, pasta / "config.json")
    return {"url": r["url"], "site_id": r["site_id"], "url_anterior": anterior}


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Monta (e publica) a página de upsell/downsell.")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--paleta", default="")
    ap.add_argument("--publicar", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    if not NUCLEO_OK:
        print("❌ A Máquina não está instalada direito (não achei o núcleo). Rode o instalar.sh de novo.",
              file=sys.stderr)
        return 1
    if args.paleta and args.paleta not in PALETAS:
        print(f'❌ Paleta "{args.paleta}" não existe. Use: {", ".join(PALETAS)}.', file=sys.stderr)
        return 1
    pasta = Path(args.pasta).resolve()
    try:
        index = montar(pasta, args.paleta or PALETA_PADRAO)
        print(f"✅ Página montada: {index}")
        if not args.publicar:
            return 0
        r = publicar(pasta)
    except KeyboardInterrupt:
        print("Cancelado.", file=sys.stderr)
        return 130
    except SemToken:
        url = _config(pasta).get("url", "")
        if url:
            print(f"ℹ️ Sua página já está no ar em {url}. Pra atualizar SEM mudar o endereço: entre na Netlify, "
                  f"abra esse site, vá na aba Deploys e arraste a pasta {pasta / 'site'} lá.")
        else:
            print("ℹ️ Sem a chave da Netlify, publique na mão:\n"
                  "   1. Entre (ou crie) sua conta na Netlify ANTES — sem login a página é apagada em ~1 hora.\n"
                  "   2. Abra https://app.netlify.com/drop\n"
                  f"   3. Arraste a pasta {pasta / 'site'}\n"
                  "   4. Copie o link e me mande (é esse que vai na plataforma como página de upsell).")
        return 3
    except (ValueError, MaquinaErro) as err:
        print(f"❌ {err}", file=sys.stderr)
        return 1
    except Exception:
        try:
            registrar_log(traceback.format_exc())
        except Exception:
            pass
        print("❌ Algo deu errado. Detalhes no log da Máquina (~/.maquina/log).", file=sys.stderr)
        return 1
    print(f"✅ No ar: {r['url']}")
    if r["url_anterior"] and r["url_anterior"] != r["url"]:
        print(f"⚠️ O endereço mudou: {r['url_anterior']} → {r['url']}. Atualize o link na sua plataforma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
