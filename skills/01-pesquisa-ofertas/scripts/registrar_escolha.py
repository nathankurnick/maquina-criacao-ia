"""Registra qual oferta o aluno escolheu: grava <projeto>/pesquisa/escolhida.json.

Uso: python registrar_escolha.py --busca <B> --oferta N --pasta-oferta <O>
A pasta da busca fica em <projeto>/pesquisa/<busca>; o arquivo vai na pasta pai (pesquisa/).
"""
import argparse
import json
import os
import sys
import traceback
from datetime import date, datetime
from pathlib import Path


def _log_tecnico(e: BaseException) -> None:
    """Grava o traceback completo em ~/.maquina/log/maquina.log. Nunca levanta erro."""
    try:
        base = Path(os.environ.get("MAQUINA_HOME") or Path.home() / ".maquina") / "log"
        base.mkdir(parents=True, exist_ok=True)
        with (base / "maquina.log").open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] registrar_escolha.py\n")
            f.write("".join(traceback.format_exception(type(e), e, e.__traceback__)) + "\n")
    except Exception:
        pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print("❌ Comando inválido. Use: registrar_escolha.py --busca <pasta da busca> --oferta N "
              "--pasta-oferta <pasta da oferta>.", file=sys.stderr)
        raise SystemExit(1)


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Registra a oferta escolhida.")
    ap.add_argument("--busca", required=True)
    ap.add_argument("--oferta", required=True)
    ap.add_argument("--pasta-oferta", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 1
    busca = Path(args.busca)
    try:
        n = int(args.oferta)
        ofertas = json.loads((busca / "ofertas.json").read_text(encoding="utf-8"))["ofertas"]
        if n < 1:
            raise IndexError
        chave = ofertas[n - 1]["chave"]
    except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
        _log_tecnico(e)
        print(f"❌ Não achei a oferta '{args.oferta}' em {busca / 'ofertas.json'}. Confira o número da tabela "
              "e a pasta da busca.", file=sys.stderr)
        return 1
    escolhida = {"busca": str(busca), "oferta": n, "chave": chave,
                 "pasta_oferta": args.pasta_oferta, "data": date.today().isoformat()}
    alvo = busca.parent / "escolhida.json"
    try:
        alvo.write_text(json.dumps(escolhida, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        _log_tecnico(e)
        print(f"❌ Não consegui gravar {alvo}. Verifique a pasta e o espaço em disco.", file=sys.stderr)
        return 1
    print(f"✅ Escolha registrada → {alvo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
