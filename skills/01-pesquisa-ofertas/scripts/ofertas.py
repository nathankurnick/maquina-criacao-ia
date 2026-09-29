"""Agrupa anúncios por oferta (destino do link) e ranqueia pelo termômetro de escala.

Tudo aqui é contagem em código: a IA só lê o resultado, nunca estima número.
Uso: python ofertas.py <anuncios.json> --saida <pasta> [--hoje AAAA-MM-DD]
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PLATAFORMAS = (
    "hotmart.com", "kiwify.com.br", "kiwify.com", "payt.com.br", "eduzz.com",
    "monetizze.com.br", "perfectpay.com.br", "braip.com", "ticto.com.br",
    "linktr.ee", "wa.me", "whatsapp.com",
)
ENCURTADORES = (
    "bit.ly", "tinyurl.com", "is.gd", "cutt.ly", "encurtador.com.br", "abre.ai",
    "rb.gy", "t.co", "linktr.ee",
)
_LOCALES = {"pt-br", "pt", "en", "es", "en-us", "es-es"}
_GENERICOS = {"marketplace", "produtos", "product", "p"}
_TRACKER = re.compile(r"(^|\.)(trk|track|tracking)\.|\.(site|click|info)$")


def _host(link: str):
    try:
        u = urlparse(link if "://" in link else "https://" + link)
        host = (u.hostname or "").lower()
    except ValueError:
        return "", None
    return (host[4:] if host.startswith("www.") else host), u


def chave_oferta(link: str) -> "str | None":
    if not link or not link.strip():
        return None
    host, u = _host(link.strip())
    if u is None:
        return None
    if host in ("l.facebook.com", "lm.facebook.com"):
        alvo = parse_qs(u.query).get("u", [""])[0]
        return chave_oferta(alvo) if alvo else None
    if not host or host.endswith(("facebook.com", "instagram.com", "fb.me", "fb.com")):
        return None
    partes = [x for x in u.path.split("/") if x]
    for e in ENCURTADORES:
        if host == e or host.endswith("." + e):
            return f"{host}/{partes[0]}" if partes else host
    for p in PLATAFORMAS:
        if host == p or host.endswith("." + p):
            segmento = next((x for x in partes if x.lower() not in _LOCALES | _GENERICOS), "")
            return f"{p}/{segmento}" if segmento else p
    return host


def parece_isca(anuncio: dict) -> bool:
    link = anuncio.get("link") or ""
    texto = re.sub(r"\s", "", anuncio.get("texto") or "")
    sinais = 0
    if link and _TRACKER.search(_host(link)[0]):
        sinais += 1
    if len(texto) < 15:
        sinais += 1
    if not chave_oferta(link):
        sinais += 1
    return sinais >= 2


def dias_no_ar(inicio: "int | None", hoje: date) -> "int | None":
    if inicio is None or isinstance(inicio, bool) or not isinstance(inicio, int):
        return None
    try:
        return (hoje - datetime.fromtimestamp(inicio, tz=timezone.utc).date()).days
    except (OverflowError, OSError, ValueError):
        return None


def termometro(volume: int, dias: "int | None") -> "tuple[float, str]":
    d = dias or 0
    pontuacao = round(volume * (1 + min(d, 90) / 30), 1)
    if volume >= 20 and d >= 30:
        selo = "🔥 escalada"
    elif volume >= 5 or d >= 14:
        selo = "📈 validando"
    else:
        selo = "🌱 em teste"
    return pontuacao, selo


def _chave_criativo(a: dict) -> str:
    for lista, prefixo in ((a.get("videos"), "v:"), (a.get("imagens"), "i:")):
        if lista:
            return prefixo + lista[0].split("?")[0].rsplit("/", 1)[-1]
    return "n:" + str(a["id"])


def _midia(anuncios: list[dict]) -> str:
    cont = Counter(a.get("midia") for a in anuncios)
    total = len(anuncios)
    if cont["video"] / total >= 0.6:
        return "vídeo"
    if cont["imagem"] / total >= 0.6:
        return "imagem"
    return "misto"


def _repeticoes(v) -> int:
    if isinstance(v, bool):
        return 1
    try:
        return max(1, int(v))
    except (TypeError, ValueError, OverflowError):
        return 1


def analisar(anuncios: list[dict], hoje: date) -> dict:
    grupos: dict[str, list[tuple[int, dict]]] = {}
    iscas = sem_link = invalidos = 0
    for posicao, a in enumerate(anuncios, start=1):
        if not isinstance(a, dict):
            invalidos += 1
            continue
        a = dict(a)
        if a.get("id") in (None, ""):
            a["id"] = f"pos{posicao}"
        a["repeticoes"] = _repeticoes(a.get("repeticoes"))
        if not isinstance(a.get("link"), str):
            a["link"] = ""
        if not isinstance(a.get("texto"), str):
            a["texto"] = ""
        if parece_isca(a):
            iscas += 1
            continue
        chave = chave_oferta(a.get("link") or "")
        if not chave:
            sem_link += 1
            continue
        grupos.setdefault(chave, []).append((posicao, a))

    ofertas = []
    for chave, itens in grupos.items():
        lista = [a for _, a in itens]
        criativos: dict[str, int] = {}
        for a in lista:
            k = _chave_criativo(a)
            criativos[k] = max(criativos.get(k, 1), a.get("repeticoes") or 1)
        volume = sum(criativos.values())
        dias = [d for d in (dias_no_ar(a.get("inicio"), hoje) for a in lista) if d is not None]
        dias_max = max(dias) if dias else None
        pontuacao, selo = termometro(volume, dias_max)
        anunciantes = [p for p, _ in Counter(a["pagina"] for a in lista if a.get("pagina")).most_common()]
        textos = [t for t, _ in Counter(a["texto"] for a in lista if (a.get("texto") or "").strip()).most_common(3)]
        ofertas.append({
            "chave": chave, "anunciantes": anunciantes, "anuncios": len(lista),
            "criativos": len(criativos), "volume": volume, "dias": dias_max,
            "midia": _midia(lista), "link": lista[0].get("link") or "",
            "posicao": itens[0][0], "textos": textos,
            "pontuacao": pontuacao, "selo": selo,
        })
    ofertas.sort(key=lambda o: (-o["pontuacao"], o["posicao"]))
    return {"ofertas": ofertas, "total_anuncios": len(anuncios),
            "descartados_isca": iscas, "sem_link": sem_link, "invalidos": invalidos}


def tabela_markdown(ofertas: list[dict], limite: int = 10) -> str:
    linhas = [
        "| # | Oferta | Anunciante | Volume | Dias no ar | Formato | Termômetro | Link |",
        "|---|---|---|---|---|---|---|---|",
    ]
    def c(v) -> str:
        return " ".join(str(v).split("\n")).replace("\r", " ").replace("|", "\\|")

    for i, o in enumerate(ofertas[:limite], start=1):
        anunciante = c(o["anunciantes"][0]) if o["anunciantes"] else "—"
        dias = "—" if o["dias"] is None else str(o["dias"])
        linhas.append(
            f"| {i} | {c(o['chave'])} | {anunciante} | {o['volume']} | {dias} | {c(o['midia'])} "
            f"| {c(o['selo'])} ({o['pontuacao']:g}) | {c(o['link'])} |"
        )
    return "\n".join(linhas) + "\n"


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description="Ranqueia ofertas a partir dos anúncios raspados.")
    ap.add_argument("anuncios")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--hoje", default="")
    args = ap.parse_args(argv)
    try:
        anuncios = json.loads(Path(args.anuncios).read_text(encoding="utf-8"))
        if not isinstance(anuncios, list):
            raise ValueError("não é uma lista")
    except (OSError, ValueError) as e:
        print(f"❌ Não consegui ler {args.anuncios} ({e}). Rode a raspagem de novo.", file=sys.stderr)
        return 1
    try:
        hoje = date.fromisoformat(args.hoje) if args.hoje else date.today()
    except ValueError:
        print(f"❌ Data inválida em --hoje: '{args.hoje}'. Use o formato AAAA-MM-DD, por exemplo 2026-09-28.",
              file=sys.stderr)
        return 1
    resultado = analisar(anuncios, hoje)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "ofertas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    tabela = tabela_markdown(resultado["ofertas"])
    (saida / "ofertas.md").write_text(tabela, encoding="utf-8")
    print(tabela)
    print(f"{resultado['total_anuncios']} anúncios lidos · {len(resultado['ofertas'])} ofertas · "
          f"{resultado['descartados_isca']} iscas descartadas · {resultado['sem_link']} sem link"
          + (f" · {resultado['invalidos']} inválidos ignorados" if resultado["invalidos"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
