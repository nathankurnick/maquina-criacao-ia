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
import urllib.parse
from pathlib import Path

_HOME = os.environ.get("MAQUINA_HOME") or os.path.expanduser("~/.maquina")
if _HOME not in sys.path:
    sys.path.append(_HOME)
try:
    from nucleo.chaves import obter_chave
    from nucleo.erros import MaquinaErro, registrar_log
    from nucleo.mockup import gerar_capa_simples, gerar_mockup
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


COPY_ABAIXO_TEXTO = "Leia a mensagem acima até o final — seu acesso aparece em seguida."


class SemToken(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print("❌ Comando incompleto (falta --pasta ou valor inválido). Use: funil_oto.py --pasta <P>/funil/upsell "
              "[--paleta nome] [--publicar] [--definir-url https://…]", file=sys.stderr)
        raise SystemExit(1)


def e(t) -> str:
    return html.escape(str(t or ""), quote=True)


def checkout_valido(url: str) -> bool:
    return bool(re.fullmatch(r"https://[^\s/]+\.[^\s]+", url or "")) and "seu-link" not in url.lower()


def embed_video(v: str) -> str:
    v = (v or "").strip()
    if v.startswith("<"):
        return f'<div class="video">{v}</div>'
    try:
        u = urllib.parse.urlparse(v)
        host = (u.hostname or "").lower()
    except ValueError:
        u, host = None, ""
    src = None
    if u and u.scheme in ("http", "https"):
        partes = [x for x in u.path.split("/") if x]
        q = urllib.parse.parse_qs(u.query)
        vid = None
        if host in ("youtu.be", "www.youtu.be") and partes:
            vid = partes[0]
        elif host == "youtube.com" or host.endswith(".youtube.com") or host == "youtube-nocookie.com" \
                or host.endswith(".youtube-nocookie.com"):
            if partes[:1] == ["watch"] and q.get("v"):
                vid = q["v"][0]
            elif len(partes) >= 2 and partes[0] in ("embed", "shorts", "live"):
                vid = partes[1]
        if vid and re.fullmatch(r"[\w-]{6,}", vid):
            src = f"https://www.youtube-nocookie.com/embed/{vid}?rel=0"
        elif host in ("vimeo.com", "www.vimeo.com", "player.vimeo.com"):
            n = next((x for x in partes if x.isdigit()), None)
            if n:
                i = partes.index(n)
                h = (q.get("h") or [""])[0]
                if not h and i + 1 < len(partes) and re.fullmatch(r"[0-9a-f]{6,}", partes[i + 1]):
                    h = partes[i + 1]
                src = f"https://player.vimeo.com/video/{n}" + (f"?h={h}" if re.fullmatch(r"\w+", h) else "")
    if not src:
        raise ValueError("o vídeo precisa ser um link do YouTube/Vimeo ou o código de incorporação do player "
                         "(VTurb, Panda…)")
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
    if oto["formato"] == "texto" and not _txt(bruto.get("copy_abaixo")):
        oto["copy_abaixo"] = COPY_ABAIXO_TEXTO
    oto["botao_html"] = _txt(bruto.get("botao_html"))
    oto["checkout_url"] = _txt(bruto.get("checkout_url"))
    oto["botao_no_player"] = bruto.get("botao_no_player") is True
    if not oto["botao_no_player"] and not oto["botao_html"] and not checkout_valido(oto["checkout_url"]):
        raise ValueError("checkout_url precisa ser o link real de pagamento do upsell (https://…), "
                         "ou cole o código do botão de 1 clique em botao_html "
                         "(ou use botao_no_player: true se o botão aparece dentro do vídeo).")
    atraso = bruto.get("atraso_segundos", 0)
    if isinstance(atraso, bool) or not isinstance(atraso, int) or atraso < 0:
        raise ValueError("atraso_segundos precisa ser um número inteiro de segundos (0 ou mais).")
    oto["atraso_segundos"] = atraso
    oto["recusar_url"] = _txt(bruto.get("recusar_url"))
    if not oto["recusar_url"]:
        raise ValueError("falta o recusar_url: é pra onde vai quem clica em \"não, obrigado\". Coloque o link da "
                         "página de downsell (se este for o upsell e houver downsell) ou o link da página de obrigado / "
                         "área de membros da plataforma (https://…).")
    if not checkout_valido(oto["recusar_url"]):
        raise ValueError("recusar_url precisa ser um endereço https:// (a próxima página: downsell ou obrigado).")
    oto["entregavel"] = _txt(bruto.get("entregavel"))
    if oto["entregavel"] and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", oto["entregavel"]):
        raise ValueError("entregavel precisa ser o nome da pasta do entregável (só minúsculas, números e hífen).")
    oto["nome_produto"] = _txt(bruto.get("nome_produto"))
    return oto


def html_oto(oto: dict, paleta_nome: str, mockup_src: str = "") -> str:
    cores = paleta(paleta_nome)
    variaveis = ":root{" + ";".join(f"--pg-{k}:{v}" for k, v in cores.items()) + "}"
    if oto["formato"] == "video":
        miolo = embed_video(oto["video"])
    else:
        paragrafos = "".join(f"<p>{e(p.strip())}</p>" for p in re.split(r"\n\s*\n", oto["texto"]) if p.strip())
        miolo = f'<div class="texto">{paragrafos}</div>'
    if mockup_src and oto["formato"] == "texto":
        miolo = f'<img class="oto-mockup" src="{e(mockup_src)}" alt="{e(oto.get("nome_produto") or "Oferta")}">' + miolo
    extra = (f'<img class="oto-mockup pequeno" src="{e(mockup_src)}" alt="{e(oto.get("nome_produto") or "Oferta")}">'
             if mockup_src and oto["formato"] == "video" else "")
    if oto.get("botao_no_player"):
        botao = ""
    else:
        botao = oto["botao_html"] or f'<a class="botao" href="{e(oto["checkout_url"])}">{e(oto["botao_texto"])}</a>'
    recusar = (f'{"<br>" if botao else ""}<a class="recusar" href="{e(oto["recusar_url"])}">'
               f'{e(oto["recusar_texto"])}</a>' if oto["recusar_url"] else "")
    classe = "oferta escondida" if oto["atraso_segundos"] > 0 else "oferta"
    script = ("<script>setTimeout(function(){var o=document.getElementById('oferta');"
              f"if(o){{o.classList.remove('escondida');}}}},{oto['atraso_segundos'] * 1000});</script>"
              if oto["atraso_segundos"] > 0 else "")
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            "<script>document.documentElement.className+=' js'</script>"
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="robots" content="noindex"><title>{e(oto["headline"])}</title>'
            f"<style>{variaveis}\n{CSS.read_text(encoding='utf-8')}</style></head><body>"
            f'<p class="aviso">{e(oto["pre_headline"])}</p><div class="caixa"><h1>{e(oto["headline"])}</h1>'
            f'{miolo}<p class="abaixo">{e(oto["copy_abaixo"])}</p>{extra}<div id="oferta" class="{classe}">{botao}{recusar}</div>'
            f"</div>{script}</body></html>\n")


def _paleta_efetiva(pasta: Path, escolhida: str = "") -> str:
    """--paleta > <P>/pagina/config.json > paleta do oferta.md > padrão (P = pasta.parents[1])."""
    if escolhida:
        return escolhida
    proj = Path(pasta).resolve().parents[1]
    try:
        dados = json.loads((proj / "pagina" / "config.json").read_text(encoding="utf-8"))
        nome = dados.get("paleta", "") if isinstance(dados, dict) else ""
        if nome in PALETAS:
            return nome
    except (OSError, ValueError):
        pass
    try:
        from nucleo.projeto import ler_oferta
        o = ler_oferta(proj)
        nome = getattr(o, "paleta", "") if o else ""
        if nome in PALETAS:
            return nome
    except Exception:  # noqa: BLE001
        pass
    return PALETA_PADRAO


def montar(pasta: Path, paleta_nome: str) -> Path:
    pasta = Path(pasta).resolve()
    mockup_arq = pasta / "mockup.png"
    documento = html_oto(ler_oto(pasta), paleta_nome, "img/mockup.png" if mockup_arq.is_file() else "")
    site, novo, antigo = pasta / "site", pasta / ".site-novo", pasta / ".site-antigo"
    if antigo.exists() and not site.exists():
        antigo.rename(site)
    for velho in (novo, antigo):
        if velho.exists():
            shutil.rmtree(velho)
    novo.mkdir()
    try:
        (novo / "index.html").write_text(documento, encoding="utf-8")
        if mockup_arq.is_file():
            (novo / "img").mkdir()
            shutil.copyfile(mockup_arq, novo / "img" / "mockup.png")
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


def definir_url(pasta: Path, url: str) -> str:
    """Grava o endereço publicado à mão (Netlify Drop) no config.json. Devolve o endereço anterior."""
    url = (url or "").strip()
    if not checkout_valido(url):
        raise ValueError("o endereço precisa começar com https:// (copie o link inteiro da Netlify).")
    pasta = Path(pasta).resolve()
    config = _config(pasta)
    anterior = config.get("url", "")
    config["url"] = url
    tmp = pasta / ".config.json.tmp"
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, pasta / "config.json")
    return anterior


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


def gerar_mockup_oto(pasta: Path, paleta_nome: str) -> dict:
    pasta = Path(pasta).resolve()
    oto = ler_oto(pasta)
    capa = pasta / "entregaveis" / oto["entregavel"] / "capa.png" if oto["entregavel"] else None
    if capa is None or not capa.is_file():
        if not oto["nome_produto"]:
            raise ValueError('pra gerar o mockup, ponha no oto.json o "entregavel" (pasta com capa.png em '
                             'entregaveis/) ou o "nome_produto".')
        capa = gerar_capa_simples(oto["nome_produto"], "Oferta especial", pasta / ".capa-oto.png", paleta_nome)
    return gerar_mockup("livro", [capa], pasta / "mockup.png", paleta_nome, obter_chave("KIE_API_KEY"))


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Monta (e publica) a página de upsell/downsell.")
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--paleta", default="")
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--definir-url", default="")
    ap.add_argument("--mockup", action="store_true")
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
    if args.mockup and args.definir_url:
        print("❌ Use --mockup sozinho; depois monte/publique a página.", file=sys.stderr)
        return 1
    if args.definir_url and args.publicar:
        print("❌ Use um de cada vez: --definir-url (guarda o link que você publicou na mão) OU --publicar "
              "— use um de cada vez.", file=sys.stderr)
        return 1
    if args.definir_url:
        if not pasta.is_dir():
            print(f"❌ Não achei a pasta {pasta}. Confira o caminho (a pasta do upsell ou do downsell).",
                  file=sys.stderr)
            return 1
        try:
            anterior = definir_url(pasta, args.definir_url)
        except (ValueError, OSError) as err:
            print(f"❌ {err}", file=sys.stderr)
            return 1
        print(f"✅ Endereço salvo: {args.definir_url.strip()}")
        if anterior and anterior != args.definir_url.strip():
            print(f"⚠️ O endereço mudou: {anterior} → {args.definir_url.strip()}. O link antigo deixou de valer: atualize na plataforma.")
        return 0
    if args.mockup and args.publicar:
        print("❌ Use --mockup sozinho; depois monte/publique a página.", file=sys.stderr)
        return 1
    try:
        if args.mockup:
            r = gerar_mockup_oto(pasta, _paleta_efetiva(pasta, args.paleta))
            if r["aviso"]:
                print(f"⚠️ O mockup saiu no modo código porque a KIE falhou: {r['aviso']}")
            print(f"✅ Mockup: {r['arquivo']}")
            return 0
        index = montar(pasta, _paleta_efetiva(pasta, args.paleta))
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
                  f"abra esse site, vá na aba Deploys e arraste a pasta {pasta / 'site'} lá. "
                  "(Arrastar em app.netlify.com/drop cria um endereço NOVO.)")
        else:
            nome = pasta.name if pasta.name in ("upsell", "downsell") else "upsell/downsell"
            print("ℹ️ A chave da Netlify não está configurada, então publique na mão (2 minutos):\n"
                  "   1. Entre (ou crie) sua conta na Netlify ANTES — sem login a página é apagada em ~1 hora.\n"
                  "   2. Abra https://app.netlify.com/drop\n"
                  f"   3. Arraste a pasta {pasta / 'site'}\n"
                  f"   4. Copie o link e me mande (é esse que vai na plataforma como página de {nome}).")
        print("   Pra publicar sozinho das próximas vezes: rode `maquina chaves` no Terminal (é interativo) "
              "e cole a chave da Netlify.")
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
