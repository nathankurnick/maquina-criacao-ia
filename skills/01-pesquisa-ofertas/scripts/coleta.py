"""Partes puras da raspagem da Biblioteca de Anúncios (porte do scrape.py do criativos-infinitos).

O Facebook embute os anúncios como JSON dentro do HTML (<script type="application/json">) e,
às vezes, em respostas GraphQL. O Coletor acha o objeto do anúncio (id + snapshot) onde quer
que ele esteja, em snake_case ou camelCase, e guarda na ORDEM de captura — como a busca vem
ordenada por impressões, essa ordem já é um ranking.
"""
import json
import re
from urllib.parse import quote

BASE_BIBLIOTECA = "https://www.facebook.com/ads/library/"
_SCRIPT_JSON = re.compile(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', re.S)


def montar_url(termo: str = "", dominio: str = "", pais: str = "BR", frase_exata: bool = False) -> str:
    if bool(termo.strip()) == bool(dominio.strip()):
        raise ValueError("Informe um termo OU um domínio (só um dos dois).")
    if dominio.strip():
        limpo = re.sub(r"^https?://", "", dominio.strip()).strip("/")
        q, tipo = quote(limpo + "/", safe=""), "keyword_unordered"
    else:
        q = quote(termo.strip(), safe="")
        tipo = "keyword_exact_phrase" if frase_exata else "keyword_unordered"
    return (
        f"{BASE_BIBLIOTECA}?active_status=active&ad_type=all&country={pais}"
        f"&is_targeted_country=false&media_type=all&q={q}&search_type={tipo}"
        "&sort_data[mode]=total_impressions&sort_data[direction]=desc"
    )


def _primeiro(item: dict, *chaves: str) -> str:
    for c in chaves:
        if item.get(c):
            return str(item[c])
    return ""


def _inteiro(v) -> "int | None":
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _normalizar(obj: dict, snap: dict, aid: str) -> dict:
    videos = [_primeiro(v, "video_hd_url", "video_sd_url", "videoHdUrl", "videoSdUrl")
              for v in (snap.get("videos") or []) if isinstance(v, dict)]
    imagens = [_primeiro(i, "original_image_url", "resized_image_url", "originalImageUrl", "resizedImageUrl")
               for i in (snap.get("images") or []) if isinstance(i, dict)]
    videos, imagens = [v for v in videos if v], [i for i in imagens if i][:3]
    cards = [c for c in (snap.get("cards") or []) if isinstance(c, dict)]
    card = cards[0] if cards else {}
    corpo = snap.get("body") or {}
    if not isinstance(corpo, dict):
        corpo = {"text": str(corpo)}
    marcacao = corpo.get("markup") if isinstance(corpo.get("markup"), dict) else {}
    texto = corpo.get("text") or marcacao.get("__html") or card.get("body") or ""
    return {
        "id": aid,
        "pagina": snap.get("page_name") or obj.get("page_name") or obj.get("pageName") or "",
        "inicio": _inteiro(obj.get("start_date") or obj.get("startDate")),
        "repeticoes": _inteiro(obj.get("collation_count") or obj.get("collationCount")),
        "cta": snap.get("cta_text") or "",
        "link": snap.get("link_url") or snap.get("linkUrl") or card.get("link_url") or "",
        "titulo": snap.get("title") or card.get("title") or "",
        "texto": str(texto)[:800],
        "videos": videos,
        "imagens": imagens,
        "midia": "video" if videos else ("imagem" if imagens else "nenhuma"),
    }


class Coletor:
    def __init__(self) -> None:
        self.anuncios: list[dict] = []
        self._vistos: set[str] = set()

    def colher(self, raiz) -> None:
        # Iterativo (pilha) pra não estourar recursão em JSON profundo; reversed mantém a ordem.
        pilha = [raiz]
        while pilha:
            obj = pilha.pop()
            if isinstance(obj, list):
                pilha.extend(reversed(obj))
                continue
            if not isinstance(obj, dict):
                continue
            aid = obj.get("ad_archive_id") or obj.get("adArchiveID")
            snap = obj.get("snapshot")
            if aid and isinstance(snap, dict) and snap:
                aid = str(aid)
                if aid not in self._vistos:
                    self._vistos.add(aid)
                    self.anuncios.append(_normalizar(obj, snap, aid))
            pilha.extend(reversed(list(obj.values())))

    def colher_html(self, html: str) -> None:
        for m in _SCRIPT_JSON.finditer(html or ""):
            bruto = m.group(1)
            for tentativa in (bruto, bruto.replace("&quot;", '"').replace("&#x2F;", "/")):
                try:
                    self.colher(json.loads(tentativa))
                    break
                except ValueError:
                    continue

    def colher_graphql(self, texto: str) -> None:
        for pedaco in re.split(r"\r?\n(?=\{)", texto or ""):
            try:
                self.colher(json.loads(pedaco))
            except ValueError:
                continue
