# skills/02-pagina-de-vendas/scripts/pagina_config.py
"""Configura a página: paleta, pixels, SEO e código extra no <head> (Utmify etc.).

Uso: python pagina_config.py --projeto P [--definir chave=valor ...] [--head-arquivo ARQ] [--paletas]
"""
import argparse
import sys
from pathlib import Path

from pagina_conteudo import CHAVES_EDITAVEIS, PALETAS_ROTULO, ler_config, salvar_config, validar_valor


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando incompleto ({message}). Use: pagina_config.py --projeto <pasta> "
              "[--definir chave=valor] [--head-arquivo arquivo] [--paletas]", file=sys.stderr)
        raise SystemExit(1)


def _mostrar(config: dict) -> None:
    for chave, valor in config.items():
        if chave == "head_html" and len(valor) > 60:
            valor = valor[:60] + f"… ({len(valor)} caracteres)"
        print(f"{chave}: {valor or '—'}")


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Configura a página de vendas.")
    ap.add_argument("--projeto", required=True)
    ap.add_argument("--definir", action="append", default=[])
    ap.add_argument("--head-arquivo", default="")
    ap.add_argument("--paletas", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    try:
        return _executar(args)
    except KeyboardInterrupt:
        print("Cancelado.", file=sys.stderr)
        return 130


def _executar(args) -> int:

    if args.paletas:
        for chave, rotulo in PALETAS_ROTULO.items():
            print(f"{chave}: {rotulo}")
        return 0

    pasta = Path(args.projeto) / "pagina"
    try:
        config = ler_config(pasta)
        novos = {}
        for par in args.definir:
            if "=" not in par:
                raise ValueError(f'"{par}" precisa ser chave=valor (ex.: paleta=preto-dourado). '
                                 f"Chaves: {', '.join(CHAVES_EDITAVEIS)}.")
            chave, valor = par.split("=", 1)
            novos[chave.strip()] = validar_valor(chave.strip(), valor)
        if args.head_arquivo:
            try:
                arq = Path(args.head_arquivo)
                if arq.stat().st_size > 100 * 1024:
                    raise ValueError("O código do <head> passou de 100 KB — confira se colou o arquivo certo.")
                novos["head_html"] = arq.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                raise ValueError(f"Não consegui ler {args.head_arquivo} ({type(e).__name__}).") from e
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    if novos:
        config.update(novos)
        try:
            salvar_config(pasta, config)
        except OSError as e:
            print(f"❌ Não consegui salvar o config.json em {pasta} ({type(e).__name__}).", file=sys.stderr)
            return 1
        print("✅ Configuração salva.")
    _mostrar(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
