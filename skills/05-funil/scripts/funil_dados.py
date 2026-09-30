# skills/05-funil/scripts/funil_dados.py
"""Lê o funil.json (ofertas, preços, conversões) e projeta o ticket médio — tudo calculado em código."""
import json
import math
import re
from pathlib import Path

REFERENCIAS = {"bump": (0.15, 0.30), "upsell": (0.10, 0.20), "downsell": (0.10, 0.20)}
META_AUMENTO = (25.0, 30.0)
N_BUMPS = 4
ETAPAS = ("upsell", "downsell")


def preco(v) -> float:
    if isinstance(v, bool) or v is None:
        raise ValueError("preço inválido")
    if isinstance(v, (int, float)):
        valor = float(v)
    elif isinstance(v, str):
        t = re.sub(r"[R$\s]", "", v)
        if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d{1,2})?|\d+(,\d{1,2})", t):
            t = t.replace(".", "").replace(",", ".")
        if not re.fullmatch(r"\d+(\.\d{1,2})?", t):
            raise ValueError(f'preço "{v}" não entendido (use 27 ou "R$ 27,90")')
        valor = float(t)
    else:
        raise ValueError("preço inválido")
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError("o preço precisa ser maior que zero")
    return valor


def conversao(v, etapa: str) -> float:
    if v is None or v == "":
        baixo, alto = REFERENCIAS[etapa]
        return (baixo + alto) / 2
    if isinstance(v, bool):
        raise ValueError("conversão inválida")
    if isinstance(v, str):
        t = v.strip().rstrip("%").replace(",", ".").strip()
        try:
            numero = float(t)
        except ValueError as err:
            raise ValueError(f'conversão "{v}" não entendida (use 0.3 ou "30%")') from err
    elif isinstance(v, (int, float)):
        numero = float(v)
    else:
        raise ValueError("conversão inválida")
    if numero == 1 and not (isinstance(v, str) and v.strip().endswith("%")) and (
            isinstance(v, int) or (isinstance(v, str) and v.strip().replace(",", ".") == "1")):
        raise ValueError('conversão "1" é ambígua: escreva 0.01 (1%) ou 1.0 (100%) — ou use "1%" ou "100%"')
    if numero > 1 or (isinstance(v, str) and v.strip().endswith("%")):
        numero /= 100
    if not math.isfinite(numero) or not 0 <= numero <= 1:
        raise ValueError(f"a conversão de {etapa} precisa estar entre 0% e 100%")
    return numero


def _etapa(bruto, nome_etapa: str, com_conversao: bool, ref: str = "") -> dict:
    if not isinstance(bruto, dict):
        raise ValueError(f'"{nome_etapa}" precisa ser um objeto com nome e preco.')
    nome = bruto.get("nome").strip() if isinstance(bruto.get("nome"), str) else ""
    if not nome:
        raise ValueError(f'"{nome_etapa}": falta o nome.')
    try:
        valor = preco(bruto.get("preco"))
    except ValueError as err:
        raise ValueError(f'"{nome_etapa}": {err} (campo preco).') from err
    d = {"nome": nome, "preco": valor}
    if com_conversao:
        try:
            d["conversao"] = conversao(bruto.get("conversao"), ref or nome_etapa)
        except ValueError as err:
            raise ValueError(f'"{nome_etapa}": {err}.') from err
    return d


def ler_funil(pasta_funil: Path) -> dict:
    arq = Path(pasta_funil) / "funil.json"
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ValueError(f"Não achei {arq}. Escreva o funil antes.") from err
    except UnicodeDecodeError as err:
        raise ValueError(f"O {arq} não está em UTF-8. Salve como UTF-8.") from err
    except (OSError, ValueError) as err:
        raise ValueError(f"O {arq} tem um erro de formatação ({type(err).__name__}).") from err
    if not isinstance(dados, dict) or "front" not in dados:
        raise ValueError(f"O {arq} precisa ter o \"front\" (nome e preco do produto principal).")
    funil = {"front": _etapa(dados["front"], "front", False)}
    if "bump" in dados and "bumps" not in dados:
        raise ValueError('O funil agora tem 4 order bumps: troque "bump" por "bumps", uma lista com os 4 '
                         "(nome, preco e conversao de cada).")
    bumps = dados.get("bumps")
    if not isinstance(bumps, list) or len(bumps) != N_BUMPS:
        raise ValueError(f'"bumps" precisa ser uma lista com os {N_BUMPS} order bumps do checkout '
                         "(nome, preco e conversao de cada).")
    funil["bumps"] = [_etapa(b, f"bump {n}", True, ref="bump") for n, b in enumerate(bumps, 1)]
    nomes = [b["nome"].casefold() for b in funil["bumps"]]
    if len(set(nomes)) != N_BUMPS:
        raise ValueError(f"Os {N_BUMPS} order bumps precisam ser ofertas diferentes (há nomes repetidos).")
    for etapa in ETAPAS:
        funil[etapa] = _etapa(dados[etapa], etapa, True) if dados.get(etapa) is not None else None
    if funil["downsell"] and not funil["upsell"]:
        raise ValueError("O downsell só aparece pra quem recusa o upsell — crie o upsell antes do downsell.")
    return funil


def projetar(funil: dict) -> dict:
    front = funil["front"]["preco"]
    partes = [{"etapa": "front", "nome": funil["front"]["nome"], "valor": front}]
    for b in funil.get("bumps") or []:
        partes.append({"etapa": "bump", "nome": b["nome"], "valor": b["preco"] * b["conversao"]})
    if funil.get("upsell"):
        u = funil["upsell"]
        partes.append({"etapa": "upsell", "nome": u["nome"], "valor": u["preco"] * u["conversao"]})
        if funil.get("downsell"):
            d = funil["downsell"]
            partes.append({"etapa": "downsell", "nome": d["nome"],
                           "valor": d["preco"] * (1 - u["conversao"]) * d["conversao"]})
    ticket = sum(p["valor"] for p in partes)
    up = funil.get("upsell")
    # a meta do método vale só para o upsell: conversão do upsell × ticket do upsell ÷ front
    aumento_upsell = up["conversao"] * up["preco"] / front * 100 if up else 0.0
    return {"ticket_medio": ticket, "aumento_pct": (ticket - front) / front * 100,
            "aumento_upsell_pct": aumento_upsell, "partes": partes}


def brl(valor: float) -> str:
    inteiro, centavos = f"{valor:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"
