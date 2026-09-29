"""Abre a Biblioteca de Anúncios num Chrome visível, rola a página e coleta os anúncios.

Uso: python raspar.py (--termo "x" | --dominio site.com | --url <url>) --saida <pasta>
     [--pais BR] [--frase-exata] [--rolagens 25]
O Facebook bloqueia navegador invisível; por isso a janela abre — o aluno não deve mexer nela.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from coleta import Coletor, montar_url

BOTOES_COOKIES = ("Allow all cookies", "Allow all", "Accept all", "Permitir todos os cookies", "Aceitar tudo")
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def rolar_e_coletar(pagina, coletor: Coletor, rolagens: int = 25) -> None:
    pagina.wait_for_timeout(4000)
    for nome in BOTOES_COOKIES:
        try:
            pagina.get_by_role("button", name=nome).first.click(timeout=1500)
            break
        except Exception:
            continue
    pagina.wait_for_timeout(2500)
    coletor.colher_html(pagina.content())
    for i in range(rolagens):
        pagina.mouse.wheel(0, 2400)
        pagina.wait_for_timeout(1100)
        if i % 3 == 0:  # DOM virtualizado: colhe durante a rolagem pra não perder cards
            coletor.colher_html(pagina.content())
    pagina.wait_for_timeout(3000)
    coletor.colher_html(pagina.content())


def abrir_e_coletar(url: str, rolagens: int = 25, coletor: "Coletor | None" = None) -> "tuple[list[dict], bool]":
    """Devolve (anúncios, interrompido). Falha ANTES do goto propaga; depois do goto devolve o parcial."""
    from playwright.sync_api import sync_playwright

    if coletor is None:
        coletor = Coletor()

    def ao_responder(resposta):
        if "graphql" in resposta.url:
            try:
                coletor.colher_graphql(resposta.text())
            except Exception:
                pass

    interrompido = False
    with sync_playwright() as p:
        opcoes = {"headless": False, "args": ["--disable-blink-features=AutomationControlled"]}
        try:
            navegador = p.chromium.launch(channel="chrome", **opcoes)
        except Exception:
            navegador = p.chromium.launch(**opcoes)
        try:
            ctx = navegador.new_context(viewport={"width": 1280, "height": 1600},
                                        locale="pt-BR", user_agent=USER_AGENT)
            pagina = ctx.new_page()
            pagina.on("response", ao_responder)
            pagina.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                rolar_e_coletar(pagina, coletor, rolagens)
            except Exception:  # janela fechada, crash, navegação destruída: fica com o que já coletou
                interrompido = True
        finally:
            try:
                navegador.close()
            except Exception:
                pass
    return coletor.anuncios, interrompido


OFERTA_MANUAL = ("Se preferir, cole aqui os links dos anúncios ou das páginas de vendas que você achou "
                 "e eu sigo no modo manual.")


def _mensagem_erro(e: BaseException) -> str:
    texto = str(e)
    if isinstance(e, ImportError) or "Executable doesn't exist" in texto:
        causa = "Não consegui abrir o navegador. Rode o instalar.sh de novo e tente outra vez."
    elif (isinstance(e, TimeoutError) or "Timeout" in type(e).__name__ or "net::" in texto):
        causa = "O Facebook demorou demais ou a internet caiu — tente de novo em alguns minutos."
    else:
        causa = "Não consegui usar o navegador pra pesquisar."
    return f"❌ {causa} (detalhe técnico: {type(e).__name__}) {OFERTA_MANUAL}"


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        if "required" in message:
            message = "faltou informar a pasta de saída (--saida)"
        elif "--rolagens" not in message:
            message = "opção não reconhecida ou faltando valor"
        print(f"❌ Comando inválido: {message}. Use --termo \"nicho\" ou --dominio site.com, "
              f"e --saida <pasta>. {OFERTA_MANUAL}", file=sys.stderr)
        raise SystemExit(1)


def _rolagens(valor: str) -> int:
    try:
        n = int(valor)
    except ValueError:
        n = 0
    if n < 1:
        raise argparse.ArgumentTypeError("--rolagens precisa ser um número inteiro maior ou igual a 1")
    return n


def _gravar(saida: Path, url: str, anuncios: list) -> None:
    (saida / "anuncios.json").write_text(json.dumps(anuncios, ensure_ascii=False, indent=2), encoding="utf-8")
    busca = {"url": url, "data": datetime.now().isoformat(timespec="seconds"), "total": len(anuncios)}
    (saida / "busca.json").write_text(json.dumps(busca, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Raspa a Biblioteca de Anúncios do Facebook.")
    ap.add_argument("--termo", default="")
    ap.add_argument("--dominio", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--pais", default="BR")
    ap.add_argument("--frase-exata", action="store_true")
    ap.add_argument("--rolagens", type=_rolagens, default=25)
    ap.add_argument("--saida", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:  # --help sai 0; qualquer erro de uso vira 1 (2 significa "sem anúncios")
        return 0 if e.code in (0, None) else 1

    try:
        url = args.url or montar_url(args.termo, args.dominio, args.pais, args.frase_exata)
    except ValueError:
        print("❌ Diga o que pesquisar: --termo \"nicho\" ou --dominio site.com (ou --url da Biblioteca). "
              + OFERTA_MANUAL, file=sys.stderr)
        return 1
    if args.url and (args.termo or args.dominio):
        print("ℹ️ Você passou --url junto com --termo/--dominio: usei a URL e ignorei o resto.")

    saida = Path(args.saida)
    try:
        saida.mkdir(parents=True, exist_ok=True)
    except OSError:
        print(f"❌ Não consegui criar a pasta de saída ({saida}). Escolha outra pasta. " + OFERTA_MANUAL,
              file=sys.stderr)
        return 1

    coletor = Coletor()
    interrompido, anuncios = False, []
    print("🔎 Abrindo a Biblioteca de Anúncios (uma janela do Chrome vai abrir — não mexa nela)...")
    try:
        anuncios, interrompido = abrir_e_coletar(url, args.rolagens, coletor)
    except KeyboardInterrupt:
        if coletor.anuncios:
            _gravar(saida, url, coletor.anuncios)
        print("Pesquisa cancelada.", file=sys.stderr)
        return 130
    except Exception as e:
        if not coletor.anuncios:
            print(_mensagem_erro(e), file=sys.stderr)
            return 1
        anuncios, interrompido = coletor.anuncios, True

    if not anuncios:
        print("❌ O Facebook não mostrou nenhum anúncio pra essa busca (pode ter bloqueado ou a busca "
              "não tem resultado). Tente outro termo, ou cole aqui os links dos anúncios/páginas que "
              "você achou e eu sigo no modo manual.", file=sys.stderr)
        return 2

    _gravar(saida, url, anuncios)
    if interrompido:
        print(f"⚠️ A pesquisa parou antes do fim, mas salvei os {len(anuncios)} anúncios coletados.")
    print(f"✅ {len(anuncios)} anúncios coletados → {saida / 'anuncios.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
