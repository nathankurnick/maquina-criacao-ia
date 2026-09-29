# nucleo/cli.py
"""Comando `maquina`: interface estável que o aluno e as skills usam."""
import argparse
import sys
import traceback
from pathlib import Path

from nucleo.caminhos import maquina_home
from nucleo.chaves import CHAVES, ler_chaves, obter_chave, salvar_chave, testar_chave
from nucleo.erros import MaquinaErro, registrar_log


def _versao(a) -> int:
    arq = maquina_home() / "VERSION"
    if not arq.exists():
        arq = Path(__file__).resolve().parent.parent / "VERSION"
    print(arq.read_text().strip() if arq.exists() else "desconhecida")
    return 0


def _status(a) -> int:
    from nucleo.projeto import listar_projetos
    print("Chaves:")
    for nome, (servico, uso, _) in CHAVES.items():
        marca = "✅" if obter_chave(nome) else "—"
        print(f"  {marca} {servico}: {uso}")
    projetos = listar_projetos()
    print(f"Projetos: {', '.join(projetos) if projetos else 'nenhum ainda'}")
    return 0


def configurar_chaves(perguntar=input, imprimir=print) -> None:
    atuais = ler_chaves()
    for nome, (servico, uso, onde) in CHAVES.items():
        situacao = "já configurada" if atuais.get(nome) else "não configurada"
        imprimir(f"\n🔑 {servico} — serve pra {uso} ({situacao}).")
        imprimir(f"   Onde pegar: {onde}")
        for _ in range(3):
            valor = perguntar(f"   Cole a chave da {servico} (ou Enter pra pular): ").strip()
            if not valor:
                imprimir("   Pulado. Sem ela, esse recurso funciona no modo manual.")
                break
            try:
                detalhe = testar_chave(nome, valor)
            except MaquinaErro as e:
                imprimir(f"   ⚠️ {e}")
                continue
            salvar_chave(nome, valor)
            imprimir(f"   ✅ {servico} ok ({detalhe})")
            break


def _chaves(a) -> int:
    configurar_chaves()
    return 0


def _projeto(a) -> int:
    from nucleo.projeto import abrir_projeto, criar_projeto, listar_projetos
    if a.acao == "novo":
        print(criar_projeto(a.valor))
    elif a.acao == "listar":
        for p in listar_projetos():
            print(p)
    else:
        print(abrir_projeto(a.valor))
    return 0


def _oferta(a) -> int:
    from nucleo.projeto import Oferta, abrir_projeto, campos_faltando, ler_oferta
    oferta = ler_oferta(abrir_projeto(a.slug)) or Oferta()
    print("\n".join(campos_faltando(oferta)))
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="maquina", description="Máquina Criação IA")
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("versao").set_defaults(func=_versao)
    sub.add_parser("status").set_defaults(func=_status)
    sub.add_parser("chaves").set_defaults(func=_chaves)
    pr = sub.add_parser("projeto")
    pr.add_argument("acao", choices=["novo", "listar", "caminho"])
    pr.add_argument("valor", nargs="?", default="")
    pr.set_defaults(func=lambda a: _projeto(a))
    of = sub.add_parser("oferta")
    of.add_argument("acao", choices=["faltando"])
    of.add_argument("slug")
    of.set_defaults(func=_oferta)
    return p


def main(argv: "list[str] | None" = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.func(args)
    except MaquinaErro as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except Exception:
        log = registrar_log(traceback.format_exc())
        print(f"❌ Algo deu errado. Mande este arquivo pro suporte: {log}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
