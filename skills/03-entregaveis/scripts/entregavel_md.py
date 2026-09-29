# skills/03-entregaveis/scripts/entregavel_md.py
"""Converte o subconjunto de Markdown que o Claude usa nos entregáveis em HTML (stdlib).

Suporta títulos (#, ##, ###), parágrafos, listas, checklist, caixas de destaque (>),
tabelas, --- , imagens locais/https e inline (negrito, itálico, código, links https).
"""
import html
import re
import unicodedata

_TIPOS_CAIXA = {"dica": "dica", "atenção": "atencao", "atencao": "atencao", "exemplo": "exemplo",
                "importante": "importante"}

_MARCA_UL = re.compile(r"^[-*]\s+")
_MARCA_OL = re.compile(r"^\d+[.)]\s+")


def _slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "secao"


def _plano(texto: str) -> str:
    t = re.sub(r"\[([^\]]+)\]\((?:[^()\s]|\([^()\s]*\))+\)", r"\1", texto)
    return re.sub(r"[*`]", "", t).strip()


def _inline(texto: str) -> str:
    t = html.escape(texto.replace("\x00", ""), quote=True)
    codigos: list[str] = []

    def guardar(m):
        codigos.append(f"<code>{m.group(1)}</code>")
        return f"\x00{len(codigos) - 1}\x00"

    t = re.sub(r"`([^`]+)`", guardar, t)

    def link(m):
        rotulo = m.group(1)
        url = html.unescape(html.unescape(m.group(2)))  # aceita &amp; digitado sem escape duplo
        if re.match(r"(?i)^https://", url):
            return f'<a href="{html.escape(url, quote=True)}">{rotulo}</a>'
        return rotulo

    t = re.sub(r"\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)", link, t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*\s][^*]*)\*(?!\*)", r"<em>\1</em>", t)
    return re.sub(r"\x00(\d+)\x00", lambda m: codigos[int(m.group(1))], t)


def _imagem(linha: str) -> "str | None":
    m = re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+)\)", linha.strip())
    if not m:
        return None
    alt, src = m.group(1), m.group(2)
    local_ok = bool(re.fullmatch(r"[A-Za-z0-9_./-]+", src)) and not src.startswith("/") \
        and ".." not in src.split("/")
    if not (local_ok or re.match(r"(?i)^https://", src)):
        return f"<p>{_inline(alt)}</p>"
    return f'<figure><img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}"></figure>'


def _celulas(linha: str) -> list[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]

_RE_CHECK = re.compile(r"^[-*]\s+\[([ xX])\]\s+(.*)$")


def _tipo_item(st: str) -> "str | None":
    if _RE_CHECK.match(st):
        return "check"
    if _MARCA_UL.match(st):
        return "ul"
    if _MARCA_OL.match(st):
        return "ol"
    return None


def _lista(linhas: list, i: int, tipo: str) -> "tuple[str, int]":
    """Lê uma lista a partir da linha i: itens, continuações indentadas e subitens (1 nível)."""
    itens: list[dict] = []
    while i < len(linhas):
        raw = linhas[i]
        if not raw.strip():
            prox = linhas[i + 1] if i + 1 < len(linhas) else ""
            recuo_p = len(prox) - len(prox.lstrip())
            if prox.strip() and ((recuo_p < 2 and _tipo_item(prox.strip()) == tipo) or recuo_p >= 2):
                i += 1
                continue
            break
        recuo = len(raw) - len(raw.lstrip())
        st = raw.strip()
        if recuo < 2:
            if _tipo_item(st) != tipo:
                break
            if tipo == "check":
                mm = _RE_CHECK.match(st)
                itens.append({"txt": [mm.group(2)], "sub": [], "feito": mm.group(1).lower() == "x"})
            else:
                marca = _MARCA_OL if tipo == "ol" else _MARCA_UL
                itens.append({"txt": [marca.sub("", st)], "sub": [], "feito": False})
        elif itens:
            if _MARCA_UL.match(st):
                itens[-1]["sub"].append([_MARCA_UL.sub("", st)])
            elif itens[-1]["sub"]:
                itens[-1]["sub"][-1].append(st)
            else:
                itens[-1]["txt"].append(st)
        else:
            break
        i += 1
    lis = []
    for it in itens:
        cls = ' class="feito"' if it["feito"] else ""
        sub = ""
        if it["sub"]:
            sub = "<ul>" + "".join(f"<li>{_inline(' '.join(s))}</li>" for s in it["sub"]) + "</ul>"
        lis.append(f"<li{cls}>{_inline(' '.join(it['txt']))}{sub}</li>")
    corpo = "".join(lis)
    if tipo == "check":
        return f'<ul class="checklist">{corpo}</ul>', i
    return f"<{tipo}>{corpo}</{tipo}>", i


def converter(texto: str) -> "tuple[str, list[dict]]":
    linhas = (texto or "").replace("\x00", "").replace("\r\n", "\n").split("\n")
    saida: list[str] = []
    titulos: list[dict] = []
    usados: dict[str, int] = {}
    i = 0

    def ident(t):
        base = _slug(t)
        usados[base] = usados.get(base, 0) + 1
        return base if usados[base] == 1 else f"{base}-{usados[base]}"

    while i < len(linhas):
        linha = linhas[i]
        s = linha.strip()
        if not s:
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.+)$", s)
        if m:
            nivel, t = len(m.group(1)), m.group(2).strip()
            plano = _plano(t)
            idt = ident(plano)
            saida.append(f'<h{nivel} id="{idt}">{_inline(t)}</h{nivel}>')
            if nivel <= 2:
                titulos.append({"nivel": nivel, "texto": plano, "id": idt})
            i += 1
            continue
        if re.fullmatch(r"-{3,}", s):
            saida.append("<hr>")
            i += 1
            continue
        img = _imagem(s)
        if img:
            saida.append(img)
            i += 1
            continue
        if s.startswith(">"):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith(">"):
                bloco.append(linhas[i].strip()[1:].strip())
                i += 1
            conteudo = " ".join(b for b in bloco if b)
            mt = re.match(r"^\*\*([^*:]+):\*\*", conteudo)
            classe = "caixa"
            if mt and mt.group(1).strip().lower() in _TIPOS_CAIXA:
                classe += " " + _TIPOS_CAIXA[mt.group(1).strip().lower()]
            saida.append(f'<aside class="{classe}"><p>{_inline(conteudo)}</p></aside>')
            continue
        if s.startswith("|") and i + 1 < len(linhas) and re.fullmatch(r"\|?\s*:?-{3,}.*", linhas[i + 1].strip()):
            cab = _celulas(s)
            i += 2
            corpo = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                corpo.append(_celulas(linhas[i]))
                i += 1
            th = "".join(f"<th>{_inline(c)}</th>" for c in cab)
            trs = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in corpo)
            saida.append(f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>")
            continue
        tipo = _tipo_item(s)
        if tipo:
            html_lista, i = _lista(linhas, i, tipo)
            saida.append(html_lista)
            continue
        par = []
        while i < len(linhas) and linhas[i].strip() and not re.match(
                r"^(#{1,3}\s|>|\||[-*]\s|\d+[.)]\s|-{3,}$|!\[)", linhas[i].strip()):
            par.append(linhas[i].strip())
            i += 1
        if not par:  # linha que parecia bloco mas não fechou (ex.: '|' sem separador)
            par.append(s)
            i += 1
        saida.append(f"<p>{_inline(' '.join(par))}</p>")
    return "\n".join(saida), titulos


def dividir_slides(texto: str) -> list[str]:
    partes, atual = [], []
    for linha in (texto or "").replace("\r\n", "\n").split("\n"):
        if re.fullmatch(r"\s*-{3,}\s*", linha):
            partes.append("\n".join(atual).strip())
            atual = []
        else:
            atual.append(linha)
    partes.append("\n".join(atual).strip())
    return [p for p in partes if p]
