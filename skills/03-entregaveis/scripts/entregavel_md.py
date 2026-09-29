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


def _inline(texto: str) -> str:
    t = html.escape(texto, quote=True)
    codigos: list[str] = []

    def guardar(m):
        codigos.append(f"<code>{m.group(1)}</code>")
        return f"\x00{len(codigos) - 1}\x00"

    t = re.sub(r"`([^`]+)`", guardar, t)

    def link(m):
        rotulo, url = m.group(1), m.group(2)
        if re.match(r"(?i)^https://", html.unescape(url)):
            return f'<a href="{url}">{rotulo}</a>'
        return rotulo

    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*\s][^*]*)\*(?!\*)", r"<em>\1</em>", t)
    return re.sub(r"\x00(\d+)\x00", lambda m: codigos[int(m.group(1))], t)


def _imagem(linha: str) -> "str | None":
    m = re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+)\)", linha.strip())
    if not m:
        return None
    alt, src = m.group(1), m.group(2)
    local_ok = not src.startswith("/") and ".." not in src.split("/") and "://" not in src and ":" not in src
    if not (local_ok or re.match(r"(?i)^https://", src)):
        return f"<p>{_inline(alt)}</p>"
    return f'<figure><img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}"></figure>'


def _celulas(linha: str) -> list[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def converter(texto: str) -> "tuple[str, list[dict]]":
    linhas = (texto or "").replace("\r\n", "\n").split("\n")
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
            idt = ident(t)
            saida.append(f'<h{nivel} id="{idt}">{_inline(t)}</h{nivel}>')
            if nivel <= 2:
                titulos.append({"nivel": nivel, "texto": t, "id": idt})
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
        if re.match(r"^[-*]\s+\[[ xX]\]\s+", s):
            itens = []
            while i < len(linhas) and re.match(r"^[-*]\s+\[[ xX]\]\s+", linhas[i].strip()):
                mm = re.match(r"^[-*]\s+\[([ xX])\]\s+(.*)$", linhas[i].strip())
                classe = ' class="feito"' if mm.group(1).lower() == "x" else ""
                itens.append(f"<li{classe}>{_inline(mm.group(2))}</li>")
                i += 1
            saida.append(f'<ul class="checklist">{"".join(itens)}</ul>')
            continue
        if re.match(r"^[-*]\s+", s):
            itens = []
            while i < len(linhas) and re.match(r"^[-*]\s+", linhas[i].strip()) \
                    and not re.match(r"^[-*]\s+\[[ xX]\]\s+", linhas[i].strip()):
                itens.append(f"<li>{_inline(_MARCA_UL.sub('', linhas[i].strip()))}</li>")
                i += 1
            saida.append(f"<ul>{''.join(itens)}</ul>")
            continue
        if re.match(r"^\d+[.)]\s+", s):
            itens = []
            while i < len(linhas) and re.match(r"^\d+[.)]\s+", linhas[i].strip()):
                itens.append(f"<li>{_inline(_MARCA_OL.sub('', linhas[i].strip()))}</li>")
                i += 1
            saida.append(f"<ol>{''.join(itens)}</ol>")
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
