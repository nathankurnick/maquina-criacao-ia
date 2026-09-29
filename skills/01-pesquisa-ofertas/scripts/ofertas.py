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
_TRACKER = re.compile(r"(^|\.)(trk|track|tracking)\.|\.(site|click|info)$")


def _host(link: str):
    u = urlparse(link if "://" in link else "https://" + link)
    host = (u.hostname or "").lower()
    return (host[4:] if host.startswith("www.") else host), u


def chave_oferta(link: str) -> "str | None":
    if not link or not link.strip():
        return None
    host, u = _host(link.strip())
    if host in ("l.facebook.com", "lm.facebook.com"):
        alvo = parse_qs(u.query).get("u", [""])[0]
        return chave_oferta(alvo) if alvo else None
    if not host or host.endswith(("facebook.com", "instagram.com", "fb.me", "fb.com")):
        return None
    if any(host == p or host.endswith("." + p) for p in PLATAFORMAS):
        segmento = next((s for s in u.path.split("/") if s), "")
        return f"{host}/{segmento}" if segmento else host
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
    if inicio is None:
        return None
    return (hoje - datetime.fromtimestamp(inicio, tz=timezone.utc).date()).days


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
    return "n:" + a["id"]


def _midia(anuncios: list[dict]) -> str:
    cont = Counter(a.get("midia") for a in anuncios)
    total = len(anuncios)
    if cont["video"] / total >= 0.6:
        return "vídeo"
    if cont["imagem"] / total >= 0.6:
        return "imagem"
    return "misto"


def analisar(anuncios: list[dict], hoje: date) -> dict:
    grupos: dict[str, list[tuple[int, dict]]] = {}
    iscas = sem_link = 0
    for posicao, a in enumerate(anuncios, start=1):
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
            "descartados_isca": iscas, "sem_link": sem_link}


def tabela_markdown(ofertas: list[dict], limite: int = 10) -> str:
    linhas = [
        "| # | Oferta | Anunciante | Anúncios | Dias no ar | Formato | Termômetro | Link |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, o in enumerate(ofertas[:limite], start=1):
        anunciante = o["anunciantes"][0] if o["anunciantes"] else "—"
        dias = "—" if o["dias"] is None else str(o["dias"])
        linhas.append(
            f"| {i} | {o['chave']} | {anunciante} | {o['volume']} | {dias} | {o['midia']} "
            f"| {o['selo']} ({o['pontuacao']:g}) | {o['link']} |"
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
    hoje = date.fromisoformat(args.hoje) if args.hoje else date.today()
    resultado = analisar(anuncios, hoje)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "ofertas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    tabela = tabela_markdown(resultado["ofertas"])
    (saida / "ofertas.md").write_text(tabela, encoding="utf-8")
    print(tabela)
    print(f"{resultado['total_anuncios']} anúncios lidos · {len(resultado['ofertas'])} ofertas · "
          f"{resultado['descartados_isca']} iscas descartadas · {resultado['sem_link']} sem link")
    return 0


if __name__ == "__main__":
    sys.exit(main())
