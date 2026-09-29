# skills/02-pagina-de-vendas/scripts/pagina_publicar.py
"""Publica a página (pasta site/) na conta Netlify do aluno e guarda site_id/url no config.json.

Uso: python pagina_publicar.py --projeto P [--pagina PASTA]
Remonta o site antes de publicar, pra o que vai ao ar ser sempre o conteudo.json/config.json atuais.
Saída: 0 publicado · 3 sem chave da Netlify (mostra como publicar na mão) · 1 erro.
"""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path

_HOME = os.environ.get("MAQUINA_HOME") or os.path.expanduser("~/.maquina")
if _HOME not in sys.path:
    sys.path.append(_HOME)

try:
    from nucleo.chaves import obter_chave  # noqa: E402
    from nucleo.erros import MaquinaErro, registrar_log  # noqa: E402
    from nucleo.netlify import publicar_pasta  # noqa: E402
    NUCLEO_OK = True
except Exception:  # ImportError ou núcleo quebrado
    NUCLEO_OK = False
    MaquinaErro = RuntimeError

from pagina_conteudo import ler_config, normalizar, salvar_config  # noqa: E402
from pagina_render import _relativa, montar_site  # noqa: E402


class SemToken(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando incompleto ({message}). Use: pagina_publicar.py --projeto <pasta do projeto>",
              file=sys.stderr)
        raise SystemExit(1)


def _remontar(pasta_projeto: Path, pagina: Path) -> None:
    try:
        _, avisos = montar_site(pasta_projeto, pagina)
    except (FileNotFoundError, ValueError) as e:
        raise MaquinaErro(str(e)) from e
    except OSError as e:
        raise MaquinaErro(f"Não consegui montar a página antes de publicar ({type(e).__name__}). "
                          "Confira se a pasta existe e se há espaço no disco.") from e
    for aviso in avisos:
        print(f"⚠️ {aviso}")


def publicar(pasta_projeto: Path, pasta_pagina: "Path | None" = None) -> dict:
    pagina = Path(pasta_pagina) if pasta_pagina else Path(pasta_projeto) / "pagina"
    site = pagina / "site"
    _remontar(Path(pasta_projeto), pagina)
    try:
        conteudo, _ = normalizar(json.loads((pagina / "conteudo.json").read_text(encoding="utf-8")))
    except (OSError, ValueError) as e:
        raise MaquinaErro(f"Não consegui ler o conteudo.json ({type(e).__name__}). Monte a página de novo.") from e
    if not conteudo["planos"]["basico"]["checkoutUrl"]:
        raise MaquinaErro("Falta o link de checkout: sem ele o botão de compra não leva a lugar nenhum. "
                          "Coloque o link no conteudo.json (planos.basico.checkoutUrl) e monte de novo.")
    token = obter_chave("NETLIFY_TOKEN")
    if not token:
        raise SemToken()
    config = ler_config(pagina)
    anterior = config.get("url") or ""
    resultado = publicar_pasta(token, site, config.get("site_id") or None)
    if anterior and anterior != resultado["url"]:
        resultado = dict(resultado, url_anterior=anterior)
    config["site_id"], config["url"] = resultado["site_id"], resultado["url"]
    try:
        salvar_config(pagina, config)
    except OSError:
        resultado = dict(resultado, aviso_config=True)
    return resultado


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Publica a página de vendas na Netlify.")
    ap.add_argument("--projeto", required=True)
    ap.add_argument("--pagina", default="")
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    if not NUCLEO_OK:
        print("❌ A Máquina não está instalada direito (não achei o núcleo). Rode o instalar.sh de novo.",
              file=sys.stderr)
        return 1
    pagina = Path(args.pagina) if args.pagina else Path(args.projeto) / "pagina"
    site = pagina / "site"
    try:
        r = publicar(Path(args.projeto), pagina)
    except SemToken:
        url = ler_config(pagina).get("url") or ""
        pasta = _relativa(args.projeto, pagina)
        if url:
            print(f"ℹ️ Sua página já está no ar em {url}. Pra atualizar SEM mudar o endereço: entre na "
                  f"Netlify, abra esse site, vá na aba Deploys e arraste a pasta {site} lá. "
                  "(Arrastar em app.netlify.com/drop cria um endereço NOVO.)\n"
                  f"   A pasta fica em {pasta}/site.")
        else:
            print("ℹ️ A chave da Netlify não está configurada, então publique na mão (2 minutos):\n"
                  "   1. Entre (ou crie) sua conta grátis na Netlify ANTES de arrastar — sem login a página "
                  "é apagada em cerca de 1 hora.\n"
                  "   2. Abra https://app.netlify.com/drop\n"
                  f"   3. Arraste a pasta {site} pra dentro da página.\n"
                  "   4. Copie o link que aparecer e me mande — é o endereço da sua página.")
        print("   Pra publicar sozinho das próximas vezes: rode `maquina chaves` no Terminal (é interativo) "
              "e cole a chave da Netlify.")
        return 3
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except MaquinaErro as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelado.", file=sys.stderr)
        return 130
    except Exception:
        try:
            registrar_log(traceback.format_exc())
        except Exception:
            pass
        print("❌ Algo deu errado ao publicar. Detalhes no log da Máquina (~/.maquina/log).", file=sys.stderr)
        return 1
    print(f"✅ No ar: {r['url']}")
    if r.get("url_anterior"):
        print(f"⚠️ O endereço da página mudou: {r['url_anterior']} → {r['url']}. "
              "Atualize o link nos seus anúncios.")
    if r.get("aviso_config"):
        print(f"⚠️ Não consegui salvar o endereço no config.json (site_id {r['site_id']}) — anote esse link.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
