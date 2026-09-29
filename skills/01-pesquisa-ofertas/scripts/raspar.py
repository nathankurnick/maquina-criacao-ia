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


def abrir_e_coletar(url: str, rolagens: int = 25) -> list[dict]:
    from playwright.sync_api import sync_playwright

    coletor = Coletor()

    def ao_responder(resposta):
        if "graphql" in resposta.url:
            try:
                coletor.colher_graphql(resposta.text())
            except Exception:
                pass

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
            rolar_e_coletar(pagina, coletor, rolagens)
        finally:
            navegador.close()
    return coletor.anuncios


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Raspa a Biblioteca de Anúncios do Facebook.")
    ap.add_argument("--termo", default="")
    ap.add_argument("--dominio", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--pais", default="BR")
    ap.add_argument("--frase-exata", action="store_true")
    ap.add_argument("--rolagens", type=int, default=25)
    ap.add_argument("--saida", required=True)
    args = ap.parse_args(argv)

    try:
        url = args.url or montar_url(args.termo, args.dominio, args.pais, args.frase_exata)
    except ValueError:
        print("❌ Diga o que pesquisar: --termo \"nicho\" ou --dominio site.com (ou --url da Biblioteca).",
              file=sys.stderr)
        return 1

    print("🔎 Abrindo a Biblioteca de Anúncios (uma janela do Chrome vai abrir — não mexa nela)...")
    try:
        anuncios = abrir_e_coletar(url, args.rolagens)
    except Exception as e:
        print("❌ Não consegui usar o navegador pra pesquisar. Rode o instalar.sh de novo e tente outra vez."
              f" (detalhe técnico: {type(e).__name__})", file=sys.stderr)
        return 1

    if not anuncios:
        print("❌ O Facebook não mostrou nenhum anúncio pra essa busca (pode ter bloqueado ou a busca "
              "não tem resultado). Tente outro termo, ou cole aqui os links dos anúncios/páginas que "
              "você achou e eu sigo no modo manual.", file=sys.stderr)
        return 2

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "anuncios.json").write_text(json.dumps(anuncios, ensure_ascii=False, indent=2), encoding="utf-8")
    busca = {"url": url, "data": datetime.now().isoformat(timespec="seconds"), "total": len(anuncios)}
    (saida / "busca.json").write_text(json.dumps(busca, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {len(anuncios)} anúncios coletados → {saida / 'anuncios.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
