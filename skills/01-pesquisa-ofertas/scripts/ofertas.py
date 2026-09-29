"""Agrupa anúncios por oferta (destino do link) e ranqueia pelo termômetro de escala.

Tudo aqui é contagem em código: a IA só lê o resultado, nunca estima número.
Uso: python ofertas.py <anuncios.json> --saida <pasta> [--hoje AAAA-MM-DD]
"""
import argparse
import json
import os
import re
import sys
import traceback
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

PLATAFORMAS = (
    "hotmart.com", "kiwify.com.br", "kiwify.com", "payt.com.br", "eduzz.com",
    "monetizze.com.br", "perfectpay.com.br", "braip.com", "ticto.com.br",
    "linktr.ee", "wa.me", "whatsapp.com",
)
ENCURTADORES = (
    "bit.ly", "tinyurl.com", "is.gd", "cutt.ly", "encurtador.com.br", "abre.ai",
    "rb.gy", "t.co", "linktr.ee",
)
# Hosts onde muitos anunciantes diferentes compartilham o mesmo endereço: a oferta é <tipo>:<página>.
HOSTS_COMPARTILHADOS = (
    ("youtube.com", "youtube"), ("youtu.be", "youtube"), ("t.me", "telegram"),
    ("m.me", "messenger"), ("messenger.com", "messenger"), ("forms.gle", "google"),
    ("docs.google.com", "google"), ("sites.google.com", "google"), ("drive.google.com", "google"),
)
_LOCALES = {"pt-br", "pt", "en", "es", "en-us", "es-es"}
_GENERICOS = {"marketplace", "produtos", "product", "p"}
_IGNORAR_SEGMENTO = _LOCALES | _GENERICOS
_TRACKER = re.compile(r"(^|\.)(trk|track|tracking)\.|\.(site|click|info)$")


def _log_tecnico(e: BaseException) -> None:
    """Grava o traceback completo em ~/.maquina/log/maquina.log. Nunca levanta erro."""
    try:
        base = Path(os.environ.get("MAQUINA_HOME") or Path.home() / ".maquina") / "log"
        base.mkdir(parents=True, exist_ok=True)
        with (base / "maquina.log").open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] ofertas.py\n")
            f.write("".join(traceback.format_exception(type(e), e, e.__traceback__)) + "\n")
    except Exception:
        pass


def _telefone(texto: str) -> str:
    digitos = re.sub(r"\D", "", unquote(texto or ""))
    return digitos if len(digitos) >= 8 else ""


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
    partes = [unquote(x) for x in u.path.split("/") if x]
    if host == "wa.me" or host == "whatsapp.com" or host.endswith(".whatsapp.com"):
        fone = _telefone(parse_qs(u.query).get("phone", [""])[0]) if partes[:1] == ["send"] or not partes \
            else _telefone(partes[0])
        return f"whatsapp/{fone}" if fone else "whatsapp:"
    for h, tipo in HOSTS_COMPARTILHADOS:
        if host == h or host.endswith("." + h):
            return f"{tipo}:"
    for e in ENCURTADORES:
        if host == e or host.endswith("." + e):
            return f"{host}/{partes[0]}" if partes else host
    for p in PLATAFORMAS:
        if host == p or host.endswith("." + p):
            segmento = next((x for x in partes if x.lower() not in _IGNORAR_SEGMENTO), "")
            return f"{p}/{segmento}" if segmento else f"{p.split('.')[0]}:"
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
        if not isinstance(a.get("pagina"), str):
            a["pagina"] = ""
        for campo in ("videos", "imagens"):
            v = a.get(campo)
            a[campo] = [x for x in v if isinstance(x, str) and x.strip()] if isinstance(v, list) else []
        if not isinstance(a.get("midia"), str):
            a["midia"] = "video" if a["videos"] else ("imagem" if a["imagens"] else "nenhuma")
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
        if chave.endswith(":"):  # host compartilhado: separa por anunciante
            chave += a["pagina"] or "?" + str(a["id"])
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
            "posicao": itens[0][0], "textos": textos, "ids": [str(a["id"]) for a in lista],
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


NENHUMA_OFERTA = ("❌ Nenhuma oferta com página de vendas nessa busca (só anúncios sem link ou de mensagem). "
                  "Tente outro termo, --dominio de um concorrente, ou o modo manual.")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        if "required" in message:
            message = "faltou informar o arquivo de anúncios e a pasta de saída (--saida)"
        elif "expected one argument" in message:
            message = "faltou o valor de uma opção (" + message.split(":")[0].replace("argument ", "") + ")"
        else:
            message = "opção não reconhecida"
        print(f"❌ Comando inválido: {message}. Use: ofertas.py <anuncios.json> --saida <pasta>.",
              file=sys.stderr)
        raise SystemExit(1)


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Ranqueia ofertas a partir dos anúncios raspados.")
    ap.add_argument("anuncios")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--hoje", default="")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 1
    try:
        anuncios = json.loads(Path(args.anuncios).read_text(encoding="utf-8"))
        if not isinstance(anuncios, list):
            raise ValueError("não é uma lista")
    except (OSError, ValueError) as e:
        _log_tecnico(e)
        print(f"❌ Não consegui ler {args.anuncios} ({type(e).__name__}). Rode a raspagem de novo.", file=sys.stderr)
        return 1
    try:
        hoje = date.fromisoformat(args.hoje) if args.hoje else date.today()
    except ValueError:
        print(f"❌ Data inválida em --hoje: '{args.hoje}'. Use o formato AAAA-MM-DD, por exemplo 2026-09-28.",
              file=sys.stderr)
        return 1
    try:
        resultado = analisar(anuncios, hoje)
    except Exception as e:
        _log_tecnico(e)
        print(f"❌ Não consegui agrupar os anúncios ({type(e).__name__}). Rode a raspagem de novo ou use "
              "o modo manual.", file=sys.stderr)
        return 1
    saida = Path(args.saida)
    tabela = tabela_markdown(resultado["ofertas"])
    try:
        saida.mkdir(parents=True, exist_ok=True)
        (saida / "ofertas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        (saida / "ofertas.md").write_text(tabela, encoding="utf-8")
    except OSError as e:
        _log_tecnico(e)
        print(f"❌ Não consegui gravar os resultados em {saida}. Escolha outra pasta e verifique o espaço "
              "no disco.", file=sys.stderr)
        return 1
    if not resultado["ofertas"]:
        print(NENHUMA_OFERTA, file=sys.stderr)
        return 2
    print(tabela)
    print(f"{resultado['total_anuncios']} anúncios lidos · {len(resultado['ofertas'])} ofertas · "
          f"{resultado['descartados_isca']} iscas descartadas · {resultado['sem_link']} sem link"
          + (f" · {resultado['invalidos']} inválidos ignorados" if resultado["invalidos"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
