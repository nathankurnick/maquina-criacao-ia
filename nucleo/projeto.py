"""Pasta do projeto do aluno e o oferta.md que liga os 5 sistemas."""
import re
import unicodedata
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import yaml

from nucleo.caminhos import pasta_projetos
from nucleo.erros import MaquinaErro

SUBPASTAS = ("pesquisa", "pagina", "entregaveis", "anuncios", "funil")
CAMPOS_OBRIGATORIOS = ("nome", "nicho", "avatar", "promessa", "mecanismo", "preco")
_LISTAS = ("entregaveis", "bonus")


@dataclass
class Oferta:
    nome: str = ""
    nicho: str = ""
    avatar: str = ""
    promessa: str = ""
    mecanismo: str = ""
    preco: str = ""
    entregaveis: list[str] = field(default_factory=list)
    bonus: list[str] = field(default_factory=list)
    garantia: str = ""
    link_checkout: str = ""
    paleta: str = ""
    corpo: str = ""


def slugify(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")
    if not slug:
        raise MaquinaErro(f'O nome "{nome}" não serve pra pasta. Use letras ou números.')
    return slug


def criar_projeto(nome: str) -> Path:
    pasta = pasta_projetos() / slugify(nome)
    for sub in SUBPASTAS:
        (pasta / sub).mkdir(parents=True, exist_ok=True)
    return pasta


def abrir_projeto(slug: str) -> Path:
    pasta = pasta_projetos() / slug
    if not pasta.is_dir():
        raise MaquinaErro(
            f'O projeto "{slug}" não existe. Veja os seus com: maquina projeto listar'
        )
    return pasta


def listar_projetos() -> list[str]:
    raiz = pasta_projetos()
    if not raiz.is_dir():
        return []
    return sorted(p.name for p in raiz.iterdir() if p.is_dir() and not p.name.startswith("."))


def _como_texto(v) -> str:
    return "" if v is None else str(v).strip()


def _como_lista(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [_como_texto(i) for i in v if _como_texto(i)]
    return [_como_texto(v)] if _como_texto(v) else []


def ler_oferta(pasta: Path) -> "Oferta | None":
    arquivo = pasta / "oferta.md"
    if not arquivo.exists():
        return None
    texto = arquivo.read_text(encoding="utf-8")
    dados, corpo = {}, texto
    if texto.startswith("---\n"):
        fim = texto.find("\n---", 4)
        if fim != -1:
            try:
                dados = yaml.safe_load(texto[4:fim]) or {}
            except yaml.YAMLError as e:
                raise MaquinaErro(
                    f"O arquivo {arquivo} tem um erro de formatação no topo (entre os ---). "
                    "Peça ao Claude pra consertar o oferta.md."
                ) from e
            corpo = texto[fim + 4:].lstrip("-").lstrip("\n")
    nomes = {f.name for f in fields(Oferta)} - {"corpo"}
    valores = {}
    for k, v in (dados if isinstance(dados, dict) else {}).items():
        if k in nomes:
            valores[k] = _como_lista(v) if k in _LISTAS else _como_texto(v)
    return Oferta(**valores, corpo=corpo.strip())


def salvar_oferta(pasta: Path, oferta: Oferta) -> Path:
    dados = asdict(oferta)
    corpo = dados.pop("corpo")
    topo = yaml.safe_dump(dados, allow_unicode=True, sort_keys=False)
    arquivo = pasta / "oferta.md"
    arquivo.write_text(f"---\n{topo}---\n\n{corpo}\n", encoding="utf-8")
    return arquivo


def campos_faltando(oferta: Oferta) -> list[str]:
    return [c for c in CAMPOS_OBRIGATORIOS if not getattr(oferta, c)]
