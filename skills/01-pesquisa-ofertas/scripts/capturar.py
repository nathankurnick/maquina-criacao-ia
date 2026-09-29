"""Captura a página de vendas de uma oferta: prints (celular) + texto + dados básicos.

Uso: python capturar.py --url <página> --saida <pasta>
O Claude lê pagina.txt e dobra.png/pagina.png pra dissecar a oferta.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PRECO = re.compile(r"R\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})?")
GARANTIA = re.compile(r"garantia[^.\n]{0,60}?\d+\s*dias", re.I)
CHECKOUTS = ("hotmart", "kiwify", "payt", "eduzz", "monetizze", "perfectpay", "braip",
             "ticto", "checkout", "pay.")
OFERTA_MANUAL = "Se preferir, mande prints e o texto da página que eu sigo com eles."


def _unicos(itens, limite=10):
    vistos, saida = set(), []
    for i in itens:
        if i not in vistos:
            vistos.add(i)
            saida.append(i)
    return saida[:limite]


def extrair_dados(texto: str, links: list[str]) -> dict:
    precos = _unicos(re.sub(r"R\$\s?", "R$ ", p) for p in PRECO.findall(texto or ""))
    checkout = _unicos(l for l in links if any(c in l.lower() for c in CHECKOUTS))
    g = GARANTIA.search(texto or "")
    return {"precos": precos, "links_checkout": checkout, "garantia": g.group(0) if g else ""}


def capturar(url: str, saida: Path) -> dict:
    from playwright.sync_api import sync_playwright

    saida.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        try:
            pagina = navegador.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
            try:
                pagina.goto(url, wait_until="networkidle", timeout=45000)
            except Exception:
                pagina.goto(url, wait_until="domcontentloaded", timeout=45000)
            pagina.wait_for_timeout(1500)
            pagina.screenshot(path=str(saida / "dobra.png"))
            pagina.screenshot(path=str(saida / "pagina.png"), full_page=True, scale="css")
            texto = pagina.inner_text("body")[:40000]
            links = pagina.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            titulo = pagina.title()
        finally:
            try:
                navegador.close()
            except Exception:  # não pode mascarar o erro original
                pass
    (saida / "pagina.txt").write_text(texto, encoding="utf-8")
    dados = {"url": url, "titulo": titulo, **extrair_dados(texto, links)}
    (saida / "dados.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return dados


def _mensagem_erro(e: BaseException) -> str:
    detalhe = str(e)
    if isinstance(e, ImportError) or "Executable doesn't exist" in detalhe:
        causa = "O navegador da Máquina não está instalado. Rode o instalar.sh de novo."
    elif isinstance(e, TimeoutError) or any(t in detalhe for t in ("Timeout", "net::", "getaddrinfo")):
        causa = "a página não abriu (link quebrado, fora do ar ou internet)."
    else:
        causa = "algo deu errado ao abrir a página."
    return f"❌ Não consegui abrir essa página: {causa} (detalhe técnico: {type(e).__name__}) {OFERTA_MANUAL}"


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        if "required" in message:
            message = "faltou informar a página (--url) e a pasta de saída (--saida)"
        elif "expected one argument" in message:
            message = "faltou o valor de uma opção (" + message.split(":")[0].replace("argument ", "") + ")"
        else:
            message = "opção não reconhecida"
        print(f"❌ Comando inválido: {message}. Use --url <página> --saida <pasta>. {OFERTA_MANUAL}",
              file=sys.stderr)
        raise SystemExit(1)


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Captura a página de vendas de uma oferta.")
    ap.add_argument("--url", required=True)
    ap.add_argument("--saida", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 1

    saida = Path(args.saida)
    try:
        saida.mkdir(parents=True, exist_ok=True)
        sonda = saida / ".teste-escrita.tmp"
        sonda.write_text("ok")
        sonda.unlink()
    except OSError:
        print(f"❌ Não consegui gravar na pasta de saída ({saida}). Escolha outra pasta. " + OFERTA_MANUAL,
              file=sys.stderr)
        return 1

    print("📸 Capturando a página da oferta...")
    try:
        dados = capturar(args.url, saida)
    except KeyboardInterrupt:
        print("Captura cancelada.", file=sys.stderr)
        return 130
    except Exception as e:
        print(_mensagem_erro(e), file=sys.stderr)
        return 1
    print(f"✅ Página capturada: {dados['titulo'] or args.url}")
    print(f"   Preços vistos: {', '.join(dados['precos']) or 'nenhum'}")
    print(f"   Checkout: {', '.join(dados['links_checkout']) or 'não achei'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
