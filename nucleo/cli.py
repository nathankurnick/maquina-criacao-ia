# nucleo/cli.py
"""Comando `maquina`: interface estável que o aluno e as skills usam."""
import argparse
import sys
import traceback
from pathlib import Path

from nucleo.caminhos import maquina_home
from nucleo.chaves import (
    CHAVES, ler_chaves, obter_chave, salvar_chave, testar_chave, validar_formato,
)
from nucleo.erros import MaquinaErro, registrar_log


def _texto_versao() -> str:
    arq = maquina_home() / "VERSION"
    if not arq.exists():
        arq = Path(__file__).resolve().parent.parent / "VERSION"
    return arq.read_text().strip() if arq.exists() else "desconhecida"


def _versao(a) -> int:
    print(_texto_versao())
    return 0


def _status(a) -> int:
    from nucleo.projeto import listar_projetos
    if a.como_json:
        import json
        print(json.dumps({
            "versao": _texto_versao(),
            "chaves": {nome: bool(obter_chave(nome)) for nome in CHAVES},
            "projetos": listar_projetos(),
        }, ensure_ascii=False))
        return 0
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
            try:
                valor = perguntar(f"   Cole a chave da {servico} (ou Enter pra pular): ").strip()
            except EOFError:
                raise MaquinaErro(
                    "Não consegui ler sua resposta aqui. Abra o Terminal e rode "
                    "`maquina chaves` direto lá.") from None
            if not valor:
                imprimir("   Pulado. Sem ela, esse recurso funciona no modo manual.")
                break
            try:
                valor = validar_formato(valor)
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
    if a.acao == "novo" and not a.valor:
        raise MaquinaErro("Faltou o nome do projeto.")
    if a.acao == "caminho" and not a.valor:
        raise MaquinaErro("Faltou o nome (slug) do projeto. Veja com: maquina projeto listar")
    if a.acao == "novo":
        print(criar_projeto(a.valor))
    elif a.acao == "listar":
        for p in listar_projetos():
            print(p)
    else:
        print(abrir_projeto(a.valor))
    return 0


_ESCALARES = ("nome", "nicho", "avatar", "promessa", "mecanismo", "preco",
              "garantia", "link_checkout", "paleta")
_LISTAS = ("entregaveis", "bonus")


def _oferta(a) -> int:
    import json
    from dataclasses import asdict
    from nucleo.projeto import (
        Oferta, abrir_projeto, campos_faltando, ler_oferta, salvar_oferta,
    )
    pasta = abrir_projeto(a.slug)
    oferta = ler_oferta(pasta) or Oferta()
    if a.acao == "faltando":
        print("\n".join(campos_faltando(oferta)))
    elif a.acao == "mostrar":
        print(json.dumps(asdict(oferta), ensure_ascii=False, indent=2))
    elif a.acao == "definir":
        if not a.extra:
            raise MaquinaErro("Faltou o que definir. Exemplo: maquina oferta definir "
                              f'{a.slug} nome="Meu Produto" preco=47')
        novos = {}
        for par in a.extra:
            campo, igual, valor = par.partition("=")
            campo = campo.strip()
            if not igual:
                raise MaquinaErro(f'"{par}" não está no formato campo=valor.')
            if campo in _LISTAS:
                raise MaquinaErro(f'"{campo}" é uma lista. Use: maquina oferta adicionar '
                                  f'{a.slug} {campo} "<item>"')
            if campo not in _ESCALARES:
                raise MaquinaErro(f'Campo desconhecido: "{campo}". Campos: {", ".join(_ESCALARES)}')
            novos[campo] = valor.strip()
        for campo, valor in novos.items():
            setattr(oferta, campo, valor)
        salvar_oferta(pasta, oferta)
    elif a.acao == "adicionar":
        if len(a.extra) != 2 or a.extra[0] not in _LISTAS or not a.extra[1].strip():
            raise MaquinaErro(f'Use: maquina oferta adicionar {a.slug} <entregaveis|bonus> "<item>"')
        lista, item = a.extra[0], a.extra[1].strip()
        atual = getattr(oferta, lista)
        if item not in atual:
            atual.append(item)
        salvar_oferta(pasta, oferta)
    return 0


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando inválido: {message}. Veja os comandos com: maquina --help",
              file=sys.stderr)
        sys.exit(2)


def _parser() -> argparse.ArgumentParser:
    p = _Parser(prog="maquina", description="Máquina Criação IA")
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("versao").set_defaults(func=_versao)
    st = sub.add_parser("status")
    st.add_argument("--json", action="store_true", dest="como_json")
    st.set_defaults(func=_status)
    sub.add_parser("chaves").set_defaults(func=_chaves)
    pr = sub.add_parser("projeto")
    pr.add_argument("acao", choices=["novo", "listar", "caminho"])
    pr.add_argument("valor", nargs="?", default="")
    pr.set_defaults(func=lambda a: _projeto(a))
    of = sub.add_parser("oferta")
    of.add_argument("acao", choices=["faltando", "definir", "adicionar", "mostrar"])
    of.add_argument("slug")
    of.add_argument("extra", nargs="*", default=[])
    of.set_defaults(func=_oferta)
    return p


def main(argv: "list[str] | None" = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.func(args)
    except MaquinaErro as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelado.", file=sys.stderr)
        return 130
    except Exception:
        log = registrar_log(traceback.format_exc())
        print(f"❌ Algo deu errado. Mande este arquivo pro suporte: {log}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
