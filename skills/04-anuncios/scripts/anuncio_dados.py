"""Lê e valida o anuncios.json que o Claude escreve; acha o link e a paleta da página do projeto."""
import json
import re
import unicodedata
from pathlib import Path

CTAS = ("Saiba mais", "Comprar agora", "Cadastre-se", "Enviar mensagem", "Ver mais", "Baixar")
LAYOUTS = ("base", "topo", "centro")
FORMATOS = ("estatico", "video")


def _slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def _txt(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _obrigatorio(bruto: dict, campo: str, onde: str) -> str:
    valor = _txt(bruto.get(campo))
    if not valor:
        raise ValueError(f"{onde}: falta o campo {campo}.")
    return valor


def _normalizar(bruto, posicao: int) -> dict:
    if not isinstance(bruto, dict):
        raise ValueError(f"anúncio #{posicao}: precisa ser um objeto com id, angulo, formato…")
    ident = _slug(_txt(bruto.get("id")))
    if not ident:
        raise ValueError(f"anúncio #{posicao}: o id precisa ter letras ou números.")
    onde = f'anúncio "{ident}"'
    formato = _txt(bruto.get("formato")).lower()
    if formato not in FORMATOS:
        raise ValueError(f"{onde}: formato precisa ser {' ou '.join(FORMATOS)}.")
    cta = _txt(bruto.get("cta")) or "Saiba mais"
    if cta not in CTAS:
        raise ValueError(f'{onde}: cta "{cta}" não existe na Meta. Use: {", ".join(CTAS)}.')
    a = {"id": ident, "angulo": _obrigatorio(bruto, "angulo", onde), "formato": formato,
         "texto_principal": _obrigatorio(bruto, "texto_principal", onde),
         "titulo": _obrigatorio(bruto, "titulo", onde), "descricao": _txt(bruto.get("descricao")), "cta": cta}
    if formato == "estatico":
        a["headline_imagem"] = _obrigatorio(bruto, "headline_imagem", onde)
        visual = bruto.get("visual") if isinstance(bruto.get("visual"), dict) else {}
        layout = _txt(visual.get("layout")) or "base"
        if layout not in LAYOUTS:
            raise ValueError(f"{onde}: layout precisa ser {', '.join(LAYOUTS)}.")
        a["visual"] = {"prompt": _txt(visual.get("prompt")), "produto": _slug(_txt(visual.get("produto"))),
                       "layout": layout}
    else:
        hooks = [h.strip() for h in bruto.get("hooks") or [] if isinstance(h, str) and h.strip()]
        if not hooks:
            raise ValueError(f"{onde}: o vídeo precisa de pelo menos 1 texto em hooks.")
        a.update(hooks=hooks, corpo=_obrigatorio(bruto, "corpo", onde),
                 cta_falado=_obrigatorio(bruto, "cta_falado", onde),
                 cenas=[c.strip() for c in bruto.get("cenas") or [] if isinstance(c, str) and c.strip()])
    return a


def ler_anuncios(pasta_anuncios: Path) -> list[dict]:
    arq = Path(pasta_anuncios) / "anuncios.json"
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ValueError(f"Não achei {arq}. Escreva os anúncios antes.") from err
    except UnicodeDecodeError as err:
        raise ValueError(f"O {arq} não está em UTF-8. Salve como UTF-8.") from err
    except (OSError, ValueError) as err:
        raise ValueError(f"O {arq} tem um erro de formatação ({type(err).__name__}).") from err
    lista = dados.get("anuncios") if isinstance(dados, dict) else None
    if not isinstance(lista, list) or not lista:
        raise ValueError(f"O {arq} precisa ter pelo menos um anúncio em \"anuncios\".")
    anuncios, vistos = [], set()
    for n, bruto in enumerate(lista, 1):
        a = _normalizar(bruto, n)
        if a["id"] in vistos:
            raise ValueError(f'O id "{a["id"]}" está repetido no {arq}.')
        vistos.add(a["id"])
        anuncios.append(a)
    return anuncios


def _config_pagina(pasta_projeto: Path) -> dict:
    try:
        dados = json.loads((Path(pasta_projeto) / "pagina" / "config.json").read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def destino(pasta_projeto: Path) -> str:
    return _txt(_config_pagina(pasta_projeto).get("url"))


def paleta_do_projeto(pasta_projeto: Path) -> str:
    return _txt(_config_pagina(pasta_projeto).get("paleta"))
