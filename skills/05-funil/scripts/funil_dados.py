# skills/05-funil/scripts/funil_dados.py
"""Lê o funil.json (ofertas, preços, conversões) e projeta o ticket médio — tudo calculado em código."""
import json
import math
import re
from pathlib import Path

REFERENCIAS = {"bump": (0.20, 0.40), "upsell": (0.10, 0.20), "downsell": (0.10, 0.20)}
META_AUMENTO = (25.0, 30.0)
ETAPAS = ("bump", "upsell", "downsell")


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
    if numero > 1 or (isinstance(v, str) and v.strip().endswith("%")):
        numero /= 100
    if not math.isfinite(numero) or not 0 <= numero <= 1:
        raise ValueError(f"a conversão de {etapa} precisa estar entre 0% e 100%")
    return numero


def _etapa(bruto, nome_etapa: str, com_conversao: bool) -> dict:
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
            d["conversao"] = conversao(bruto.get("conversao"), nome_etapa)
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
    for etapa in ETAPAS:
        funil[etapa] = _etapa(dados[etapa], etapa, True) if dados.get(etapa) is not None else None
    if funil["downsell"] and not funil["upsell"]:
        raise ValueError("O downsell só aparece pra quem recusa o upsell — crie o upsell antes do downsell.")
    return funil


def projetar(funil: dict) -> dict:
    front = funil["front"]["preco"]
    partes = [{"etapa": "front", "nome": funil["front"]["nome"], "valor": front}]
    if funil.get("bump"):
        b = funil["bump"]
        partes.append({"etapa": "bump", "nome": b["nome"], "valor": b["preco"] * b["conversao"]})
    if funil.get("upsell"):
        u = funil["upsell"]
        partes.append({"etapa": "upsell", "nome": u["nome"], "valor": u["preco"] * u["conversao"]})
        if funil.get("downsell"):
            d = funil["downsell"]
            partes.append({"etapa": "downsell", "nome": d["nome"],
                           "valor": d["preco"] * (1 - u["conversao"]) * d["conversao"]})
    ticket = sum(p["valor"] for p in partes)
    return {"ticket_medio": ticket, "aumento_pct": (ticket - front) / front * 100, "partes": partes}


def brl(valor: float) -> str:
    inteiro, centavos = f"{valor:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"
