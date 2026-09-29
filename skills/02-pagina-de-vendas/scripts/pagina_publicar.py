# skills/02-pagina-de-vendas/scripts/pagina_publicar.py
"""Publica a página (pasta site/) na conta Netlify do aluno e guarda site_id/url no config.json.

Uso: python pagina_publicar.py --projeto P
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
except ImportError:
    NUCLEO_OK = False
    MaquinaErro = RuntimeError

from pagina_conteudo import ler_config, normalizar, salvar_config  # noqa: E402


class SemToken(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando incompleto ({message}). Use: pagina_publicar.py --projeto <pasta do projeto>",
              file=sys.stderr)
        raise SystemExit(1)


def publicar(pasta_projeto: Path) -> dict:
    pagina = Path(pasta_projeto) / "pagina"
    site = pagina / "site"
    if not (site / "index.html").exists():
        raise MaquinaErro("A página ainda não foi montada. Rode o pagina_render.py antes de publicar.")
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
    resultado = publicar_pasta(token, site, config.get("site_id") or None)
    config["site_id"], config["url"] = resultado["site_id"], resultado["url"]
    try:
        salvar_config(pagina, config)
    except OSError:
        resultado = dict(resultado, aviso_config=True)
    return resultado


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Publica a página de vendas na Netlify.")
    ap.add_argument("--projeto", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    if not NUCLEO_OK:
        print("❌ A Máquina não está instalada direito (não achei o núcleo). Rode o instalar.sh de novo.",
              file=sys.stderr)
        return 1
    site = Path(args.projeto) / "pagina" / "site"
    try:
        r = publicar(Path(args.projeto))
    except SemToken:
        print("ℹ️ A chave da Netlify não está configurada, então publique na mão (1 minuto):\n"
              "   1. Abra https://app.netlify.com/drop (crie a conta grátis se pedir).\n"
              f"   2. Arraste a pasta {site} pra dentro da página.\n"
              "   3. Copie o link que aparecer — é o endereço da sua página.\n"
              "   Pra publicar sozinho das próximas vezes: rode `maquina chaves` e cole a chave da Netlify.")
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
    if r.get("aviso_config"):
        print(f"⚠️ Não consegui salvar o endereço no config.json (site_id {r['site_id']}) — anote esse link.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
