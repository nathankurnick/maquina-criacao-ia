"""Captura a página de vendas de uma oferta: prints (celular) + texto + dados básicos.

Uso: python capturar.py --url <página> --saida <pasta>
O Claude lê pagina.txt e dobra.png/pagina-NN.png pra dissecar a oferta.
"""
import argparse
import json
import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

PRECO = re.compile(r"R\$\s?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{2})?")
GARANTIA = re.compile(
    r"garantia[^.\n]{0,60}?\d+\s*(?:\([^)\n]{0,20}\)\s*)?(?:dias|anos?|m[eê]s(?:es)?)\b"
    r"|\d+\s*(?:\([^)\n]{0,20}\)\s*)?dias\s+de\s+garantia", re.I)
DOMINIOS_CHECKOUT = ("hotmart.com", "kiwify.com.br", "kiwify.com", "payt.com.br", "eduzz.com",
                     "monetizze.com.br", "perfectpay.com.br", "braip.com", "ticto.com.br")
USER_AGENT_MOVEL = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
                    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
FATIA_ALTURA = 2400
MAX_FATIAS = 20
LARGURA_MAX = 1280
SAIDAS_ANTIGAS = ("dobra.png", "pagina.png", "pagina.txt", "dados.json")
OFERTA_MANUAL = "Se preferir, mande prints e o texto da página que eu sigo com eles."


def _log_tecnico(e: BaseException) -> None:
    """Grava o traceback completo em ~/.maquina/log/maquina.log. Nunca levanta erro."""
    try:
        base = Path(os.environ.get("MAQUINA_HOME") or Path.home() / ".maquina") / "log"
        base.mkdir(parents=True, exist_ok=True)
        with (base / "maquina.log").open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] capturar.py\n")
            f.write("".join(traceback.format_exception(type(e), e, e.__traceback__)) + "\n")
    except Exception:
        pass


def _unicos(itens, limite=10):
    vistos, saida = set(), []
    for i in itens:
        if i not in vistos:
            vistos.add(i)
            saida.append(i)
    return saida[:limite]


def _eh_checkout(link: str) -> bool:
    try:
        u = urlparse(link)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    if any(host == d or host.endswith("." + d) for d in DOMINIOS_CHECKOUT):
        return True
    if host.split(".")[0] in ("pay", "checkout") and "." in host:
        return True
    return "checkout" in [seg.lower() for seg in u.path.split("/")]


def extrair_dados(texto: str, links: list[str]) -> dict:
    precos = _unicos(re.sub(r"R\$\s?", "R$ ", p) for p in PRECO.findall(texto or ""))
    checkout = _unicos(l for l in links if _eh_checkout(l))
    g = GARANTIA.search(texto or "")
    return {"precos": precos, "links_checkout": checkout, "garantia": g.group(0) if g else ""}


def _limpar(saida: Path) -> None:
    for nome in SAIDAS_ANTIGAS:
        (saida / nome).unlink(missing_ok=True)
    for f in saida.glob("pagina-[0-9][0-9].png"):
        f.unlink(missing_ok=True)


def capturar(url: str, saida: Path) -> dict:
    from playwright.sync_api import sync_playwright

    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "https://" + url
    saida.mkdir(parents=True, exist_ok=True)
    _limpar(saida)
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        try:
            contexto = navegador.new_context(
                viewport={"width": 390, "height": 844}, device_scale_factor=2,
                is_mobile=True, has_touch=True, user_agent=USER_AGENT_MOVEL)
            pagina = contexto.new_page()
            pagina.goto(url, wait_until="load", timeout=45000)
            try:
                pagina.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            for _ in range(60):  # rola até o fim pra disparar lazy-load
                pos = pagina.evaluate("() => { window.scrollBy(0, 900); return "
                                      "[window.scrollY + window.innerHeight, document.documentElement.scrollHeight]; }")
                pagina.wait_for_timeout(150)
                if pos[0] >= min(pos[1], MAX_FATIAS * FATIA_ALTURA) - 2:
                    break
            pagina.evaluate("() => window.scrollTo(0, 0)")
            pagina.wait_for_timeout(800)
            altura = int(pagina.evaluate("() => document.documentElement.scrollHeight"))
            largura = min(LARGURA_MAX, int(pagina.evaluate(
                "() => Math.max(document.documentElement.scrollWidth, "
                "document.body ? document.body.scrollWidth : 0, window.innerWidth)")))
            capturada = min(altura, MAX_FATIAS * FATIA_ALTURA)
            pagina.screenshot(path=str(saida / "dobra.png"))
            prints = []
            for i in range(min(MAX_FATIAS, max(1, -(-altura // FATIA_ALTURA)))):
                y = i * FATIA_ALTURA
                nome = f"pagina-{i + 1:02d}.png"
                pagina.screenshot(path=str(saida / nome), full_page=True, scale="css",
                                  clip={"x": 0, "y": y, "width": largura, "height": min(FATIA_ALTURA, altura - y)})
                prints.append(nome)
            texto = pagina.inner_text("body")[:40000]
            links = pagina.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            titulo = pagina.title()
            url_final = pagina.url
        finally:
            try:
                navegador.close()
            except Exception:  # não pode mascarar o erro original
                pass
    (saida / "pagina.txt").write_text(texto, encoding="utf-8")
    dados = {"url": url, "url_final": url_final, "titulo": titulo, "altura": altura, "altura_capturada": capturada,
             "truncada": altura > MAX_FATIAS * FATIA_ALTURA, "largura": largura, "prints": prints,
             **extrair_dados(texto, links)}
    (saida / "dados.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return dados


def _mensagem_erro(e: BaseException) -> str:
    detalhe = str(e)
    if "Download is starting" in detalhe:
        causa = "esse link é um arquivo, não uma página."
    elif isinstance(e, ImportError) or "Executable doesn't exist" in detalhe:
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
        _limpar(saida)
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
        _log_tecnico(e)
        print(_mensagem_erro(e), file=sys.stderr)
        return 1
    print(f"✅ Página capturada: {dados['titulo'] or args.url}")
    if dados.get("truncada"):
        print(f"⚠️ Página muito longa: capturei só os primeiros {dados['altura_capturada']} px.")
    print(f"   Preços vistos: {', '.join(dados['precos']) or 'nenhum'}")
    print(f"   Checkout: {', '.join(dados['links_checkout']) or 'não achei'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
