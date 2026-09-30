"""Conteúdo da página de vendas (porte do content-schema.ts do Gerador), paletas, ícones
e o config.json da página.

normalizar() aceita o JSON que o Claude escreveu (com campos a mais, a menos ou tipos
errados) e devolve um conteúdo íntegro + avisos explicando cada bloco que ficou escondido.
"""
import json
import math
import os
import re
import tempfile
from pathlib import Path

DISCLAIMER_PADRAO = (
    "Este material é de natureza educacional e informativa. Os resultados variam conforme "
    "a aplicação, o esforço e o contexto de cada pessoa, e não há garantia de resultado específico."
)

PALETAS = {
    "azul-laranja": {"fundo": "#0a1628", "fundo-claro": "#eef3fb", "fundo-medio": "#0f3460",
                     "destaque": "#f59e0b", "cta": "#f59e0b", "cta-texto": "#0a1628",
                     "texto-claro": "#ffffff", "texto-escuro": "#0a1628"},
    "preto-dourado": {"fundo": "#0c0c0c", "fundo-claro": "#f6f3ec", "fundo-medio": "#1c1a16",
                      "destaque": "#d4af37", "cta": "#d4af37", "cta-texto": "#0c0c0c",
                      "texto-claro": "#ffffff", "texto-escuro": "#0c0c0c"},
    "verde-branco": {"fundo": "#06281c", "fundo-claro": "#eef8f2", "fundo-medio": "#0c4230",
                     "destaque": "#22c55e", "cta": "#22c55e", "cta-texto": "#052e1b",
                     "texto-claro": "#ffffff", "texto-escuro": "#06281c"},
    "vermelho-preto": {"fundo": "#120a0a", "fundo-claro": "#f8f0ef", "fundo-medio": "#2a1111",
                       "destaque": "#ef4444", "cta": "#ef4444", "cta-texto": "#ffffff",
                       "texto-claro": "#ffffff", "texto-escuro": "#120a0a"},
    "grafite-ciano": {"fundo": "#101820", "fundo-claro": "#eef4f7", "fundo-medio": "#1c2b36",
                      "destaque": "#06b6d4", "cta": "#06b6d4", "cta-texto": "#04222b",
                      "texto-claro": "#ffffff", "texto-escuro": "#101820"},
}
PALETA_PADRAO = "azul-laranja"
PALETAS_ROTULO = {
    "azul-laranja": "Azul e laranja", "preto-dourado": "Preto e dourado",
    "verde-branco": "Verde e branco", "vermelho-preto": "Vermelho e preto",
    "grafite-ciano": "Grafite e ciano",
}

ICONES = {
    "livro": ["M4 4h12a2 2 0 0 1 2 2v14H6a2 2 0 0 1-2-2V4z", "M6 20a2 2 0 0 1 0-4h12"],
    "busca": ["M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z", "M16.5 16.5 21 21"],
    "estrela": ["M12 3l2.7 6.1 6.6.6-5 4.4 1.5 6.4L12 17.6 6.2 20.5l1.5-6.4-5-4.4 6.6-.6z"],
    "camera": ["M3 8h4l2-3h6l2 3h4v11H3z", "M12 9.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z"],
    "etiqueta": ["M3 3h8l10 10-8 8L3 11z", "M7.5 6a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"],
    "trofeu": ["M7 4h10v5a5 5 0 0 1-10 0z", "M7 6H4v2a3 3 0 0 0 3 3", "M17 6h3v2a3 3 0 0 1-3 3",
               "M12 14v5", "M9 21h6"],
    "ferramenta": ["M20 5a4 4 0 0 1-5.4 5.4L6 19a2 2 0 1 1-3-3l8.6-8.6A4 4 0 0 1 17 2l-2.5 2.5 2.5 2.5L20 5z"],
    "lista": ["M8 6h13", "M8 12h13", "M8 18h13", "M3.5 6h.01", "M3.5 12h.01", "M3.5 18h.01"],
    "relogio": ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 7v5l3 2"],
    "escudo": ["M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"],
    "calculadora": ["M6 3h12v18H6z", "M9 7h6", "M9 11h.01", "M12 11h.01", "M15 11h.01",
                    "M9 15h.01", "M12 15h.01", "M15 15h.01", "M9 19h6"],
    "documento": ["M7 3h7l5 5v13H7z", "M14 3v5h5"],
}
ICONE_PADRAO = "estrela"

CONFIG_PADRAO = {
    "paleta": PALETA_PADRAO, "pixel_meta": "", "pixel_google": "", "head_html": "",
    "seo_titulo": "", "seo_descricao": "", "site_id": "", "url": "",
}
CHAVES_EDITAVEIS = ("paleta", "pixel_meta", "pixel_google", "head_html", "seo_titulo", "seo_descricao", "url")


def _objeto(v) -> dict:
    return v if isinstance(v, dict) else {}


def _lista(v) -> list:
    return v if isinstance(v, list) else []


def _texto(v, padrao: str = "") -> str:
    if isinstance(v, str) and v.strip():
        return v.strip()
    return padrao


_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def _slug(v) -> str:
    t = _texto(v)
    return t if _SLUG.fullmatch(t) else ""


def _preco(v) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
        return str(int(v)) if float(v).is_integer() else str(v)
    return _texto(v)


def _bool(v, padrao: bool) -> bool:
    return v if isinstance(v, bool) else padrao


def _inteiro(v, padrao: int) -> int:
    if isinstance(v, str) and re.fullmatch(r"\d+", v.strip()):
        return int(v.strip())
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return padrao
    return int(v)


def _titulo_descricao(v) -> dict:
    o = _objeto(v)
    return {"titulo": _texto(o.get("titulo")), "descricao": _texto(o.get("descricao"))}


def url_segura(u: str) -> bool:
    u = (u or "").strip()
    return bool(re.match(r"(?i)https?://[^\s]+$", u) or re.match(r"#\S*$", u)
                or (re.match(r"/(?![/\\])\S*$", u) is not None))


def checkout_valido(u: str) -> bool:
    """Link de pagamento: só https com host real, e nunca o texto-modelo SEU-LINK."""
    u = (u or "").strip()
    return bool(re.fullmatch(r"https://[^\s/]+\.[^\s]+", u)) and "seu-link" not in u.lower()


def _plano(v, nome_padrao: str, ativo_padrao: bool, destaque: bool) -> dict:
    o = _objeto(v)
    return {
        "ativo": _bool(o.get("ativo"), ativo_padrao),
        "nome": _texto(o.get("nome"), nome_padrao),
        "itens": [t for t in (_texto(i) for i in _lista(o.get("itens"))) if t],
        "precoDe": _preco(o.get("precoDe")),
        "precoPor": _preco(o.get("precoPor")),
        "checkoutUrl": _texto(o.get("checkoutUrl")),
        "cta": _texto(o.get("cta"), "QUERO ACESSAR AGORA"),
        "destaque": _bool(o.get("destaque"), destaque),
    }


def normalizar(bruto: object) -> "tuple[dict, list[str]]":
    raiz = _objeto(bruto)
    avisos: list[str] = []

    def bloco(nome):
        return _objeto(raiz.get(nome))

    h = bloco("hero")
    hero = {"ativo": _bool(h.get("ativo"), True), "badge": _texto(h.get("badge")),
            "headline": _texto(h.get("headline")), "subheadline": _texto(h.get("subheadline")),
            "cta": _texto(h.get("cta"), "QUERO ACESSAR AGORA"),
            "entregavel": _slug(h.get("entregavel"))}
    if hero["ativo"] and not hero["headline"]:
        hero["ativo"] = False
        avisos.append("hero: sem headline — o topo da página não aparece.")

    c = bloco("carrossel")
    carrossel = {"ativo": _bool(c.get("ativo"), True),
                 "titulo": _texto(c.get("titulo"), "Veja o material por dentro"),
                 "descricao": _texto(c.get("descricao"))}

    def com_itens(nome, campos_extra, montar_item):
        b = bloco(nome)
        d = {"ativo": _bool(b.get("ativo"), True), **{k: _texto(b.get(k)) for k in campos_extra}}
        d["itens"] = [i for i in (montar_item(x) for x in _lista(b.get("itens"))) if i["titulo"]]
        if d["ativo"] and not d["itens"]:
            d["ativo"] = False
            avisos.append(f"{nome}: sem itens — a seção fica escondida.")
        return d

    para_quem = com_itens("paraQuem", ("titulo", "subtitulo"), _titulo_descricao)
    conteudo = com_itens("conteudo", ("titulo", "subtitulo"), lambda x: {
        "icone": (i if isinstance(i := _objeto(x).get("icone"), str) and i in ICONES else ICONE_PADRAO),
        **_titulo_descricao(x)})
    incluso = com_itens("incluso", ("titulo", "nota"), _titulo_descricao)
    entrega = com_itens("entrega", ("titulo", "subtitulo"), _titulo_descricao)
    bonus = com_itens("bonus", ("titulo", "subtitulo"), lambda x: {
        **_titulo_descricao(x), "valor": _preco(_objeto(x).get("valor")),
        "entregavel": _slug(_objeto(x).get("entregavel"))})

    d = bloco("depoimentos")
    depoimentos = {"ativo": _bool(d.get("ativo"), True),
                   "titulo": _texto(d.get("titulo"), "Veja o que estão dizendo"),
                   "subtitulo": _texto(d.get("subtitulo"))}

    p = bloco("planos")
    basico = _plano(p.get("basico"), "PLANO BÁSICO", True, False)
    premium = _plano(p.get("premium"), "PLANO PREMIUM", False, True)
    for pl in (basico, premium):
        if pl["checkoutUrl"] and not checkout_valido(pl["checkoutUrl"]):
            pl["checkoutUrl"] = ""
            pl["ativo"] = False
            aviso = ("planos: o link de checkout precisa ser o endereço real de pagamento, começando com "
                     "https:// (ex.: https://pay.kiwify.com.br/…)")
            if aviso not in avisos:
                avisos.append(aviso)
    if premium["ativo"] and (not premium["checkoutUrl"] or premium["checkoutUrl"] == basico["checkoutUrl"]):
        premium["ativo"] = False
        avisos.append("planos: o premium está sem link ou com o mesmo checkout do básico — escondido.")
    if basico["ativo"] and not basico["checkoutUrl"]:
        basico["ativo"] = False
        avisos.append("planos: falta o link de checkout do plano básico — os botões não levam ao pagamento.")
    planos = {"ativo": _bool(p.get("ativo"), True),
              "titulo": _texto(p.get("titulo"), "Escolha o melhor plano para você"),
              "subtitulo": _texto(p.get("subtitulo")), "basico": basico, "premium": premium}
    if not basico["ativo"] and not premium["ativo"]:
        planos["ativo"] = False

    g = bloco("garantia")
    garantia = {"ativo": _bool(g.get("ativo"), True),
                "titulo": _texto(g.get("titulo"), "GARANTIA INCONDICIONAL"),
                "dias": _inteiro(g.get("dias"), 7), "texto": _texto(g.get("texto")),
                "cta": _texto(g.get("cta"), "GARANTIR MEU ACESSO AGORA")}
    if g.get("dias") is not None and _inteiro(g.get("dias"), -1) < 0:
        avisos.append("garantia: dias inválido — usei 7.")
    if garantia["ativo"] and not garantia["texto"]:
        garantia["ativo"] = False
        avisos.append("garantia: sem texto — a seção fica escondida.")

    f = bloco("faq")
    faq = {"ativo": _bool(f.get("ativo"), True), "titulo": _texto(f.get("titulo"), "Perguntas Frequentes"),
           "itens": [i for i in ({"pergunta": _texto(_objeto(x).get("pergunta")),
                                  "resposta": _texto(_objeto(x).get("resposta"))}
                                 for x in _lista(f.get("itens"))) if i["pergunta"] and i["resposta"]]}
    if faq["ativo"] and not faq["itens"]:
        faq["ativo"] = False
        avisos.append("faq: sem perguntas — a seção fica escondida.")

    r = bloco("rodape")
    disclaimer = _texto(r.get("disclaimer"))
    rodape = {"ativo": True, "nomeProduto": _texto(r.get("nomeProduto")),
              "disclaimer": ("" if disclaimer == "-" else
                             disclaimer if len(disclaimer) >= 20 else DISCLAIMER_PADRAO)}

    return ({"hero": hero, "carrossel": carrossel, "paraQuem": para_quem, "conteudo": conteudo,
             "incluso": incluso, "entrega": entrega, "bonus": bonus, "depoimentos": depoimentos,
             "planos": planos, "garantia": garantia, "faq": faq, "rodape": rodape}, avisos)


def ler_config(pasta_pagina: Path) -> dict:
    arq = Path(pasta_pagina) / "config.json"
    config = dict(CONFIG_PADRAO)
    if not arq.exists():
        return config
    try:
        bruto = json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"Não consegui ler {arq} ({e}). Apague o config.json e configure de novo.") from e
    for chave in CONFIG_PADRAO:
        v = _objeto(bruto).get(chave)
        if isinstance(v, str):
            config[chave] = v
    if config["paleta"] not in PALETAS:
        config["paleta"] = PALETA_PADRAO
    return config


def salvar_config(pasta_pagina: Path, config: dict) -> Path:
    pasta = Path(pasta_pagina)
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / "config.json"
    dados = {k: config.get(k, CONFIG_PADRAO[k]) for k in CONFIG_PADRAO}
    fd, tmp = tempfile.mkstemp(dir=pasta, prefix=".config.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(tmp, arq)
        os.chmod(arq, 0o644)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return arq


def validar_valor(chave: str, valor: str) -> str:
    if not isinstance(valor, str):
        raise ValueError("O valor precisa ser um texto.")
    v = valor.strip()
    if chave not in CHAVES_EDITAVEIS:
        raise ValueError(f'"{chave}" não pode ser mudado aqui. Use: {", ".join(CHAVES_EDITAVEIS)}.')
    if chave == "paleta" and v not in PALETAS:
        raise ValueError(f'Paleta "{v}" não existe. Opções: {", ".join(PALETAS)}.')
    if chave == "pixel_meta" and v and not re.fullmatch(r"\d{8,20}", v):
        raise ValueError("O ID do Pixel da Meta tem só números (8 a 20 dígitos).")
    if chave == "pixel_google" and v and not re.fullmatch(r"(G|AW|GT)-[A-Z0-9]+", v):
        raise ValueError('O ID do Google começa com "G-" ou "AW-" (ex.: G-ABC123).')
    if chave == "url" and v and not re.fullmatch(r"https://[^\s/]+\.[^\s]+", v):
        raise ValueError("O endereço da página precisa começar com https:// (ex.: https://minha-pagina.netlify.app).")
    return v if chave != "head_html" else valor
