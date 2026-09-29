# skills/04-anuncios/scripts/anuncio_exportar.py
"""Exporta o que o aluno sobe no Gerenciador de Anúncios: textos.md, roteiros.md e o plano de teste.

Uso: python anuncio_exportar.py --projeto <P>
"""
import argparse
import csv
import io
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

_SKILL03 = Path.home() / ".claude" / "skills" / "03-entregaveis" / "scripts"
if _SKILL03.is_dir() and str(_SKILL03) not in sys.path:
    sys.path.append(str(_SKILL03))
try:
    from entregavel_planilha import gerar_xlsx
except Exception:  # noqa: BLE001 — sem o Sistema 03, o plano sai em CSV
    gerar_xlsx = None

from anuncio_dados import destino, ler_anuncios  # noqa: E402
from anuncio_riscos import avaliar  # noqa: E402

COLUNAS = ["Anúncio", "Ângulo", "Formato", "Criativo/Hook", "Público", "Orçamento/dia (R$)", "Status", "Resultado"]


def _seguro(v):
    """Célula que começa com = + - @ vira fórmula no Excel; um espaço na frente segura."""
    return f" {v}" if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v


def _registrar_log(texto: str) -> None:
    try:
        home = Path(os.environ.get("MAQUINA_HOME") or os.path.expanduser("~/.maquina"))
        (home / "log").mkdir(parents=True, exist_ok=True)
        with (home / "log" / "maquina.log").open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {texto}\n")
    except Exception:  # noqa: BLE001 — log nunca derruba o comando
        pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print("❌ Comando incompleto ou com opção desconhecida. Use: anuncio_exportar.py --projeto <P>", file=sys.stderr)
        raise SystemExit(1)


def _avisos_md(anuncio: dict) -> str:
    avisos = avaliar(anuncio)
    return "".join(f"\n> ⚠️ {a}" for a in avisos) + ("\n" if avisos else "")


def textos_md(anuncios: list[dict], link: str, pasta_criativos: Path) -> str:
    partes = ["# Textos dos anúncios estáticos\n",
              "Pra cada anúncio: suba as imagens, cole o texto principal, o título, a descrição, escolha o botão e o link.\n"]
    for a in anuncios:
        if a["formato"] != "estatico":
            continue
        arquivos = [f"{a['id']}-{fmt}.jpg" for fmt in ("1x1", "9x16")
                    if (Path(pasta_criativos) / f"{a['id']}-{fmt}.jpg").exists()]
        partes.append(
            f"\n## {a['id']} — {a['angulo']}\n\n"
            f"- **Imagens:** {', '.join(arquivos) if arquivos else 'ainda não montadas (rode o anuncio_criativo.py)'}\n"
            f"- **Texto principal:**\n\n{a['texto_principal']}\n\n"
            f"- **Título:** {a['titulo']}\n"
            f"- **Descrição:** {a['descricao'] or '—'}\n"
            f"- **Botão:** {a['cta']}\n"
            f"- **Link:** {link or '⚠️ Publique a página no Sistema 02 e cole o link aqui'}\n"
            f"{_avisos_md(a)}")
    return "".join(partes)


def roteiros_md(anuncios: list[dict]) -> str:
    videos = [a for a in anuncios if a["formato"] == "video"]
    if not videos:
        return ""
    partes = ["# Roteiros dos anúncios em vídeo\n",
              "Grave um vídeo por hook: o hook muda, o corpo e o final são os mesmos. Assim você testa o começo barato.\n"]
    for a in videos:
        hooks = "\n".join(f"- **Hook {n}:** {h}" for n, h in enumerate(a["hooks"], 1))
        cenas = "\n".join(f"{n}. {c}" for n, c in enumerate(a["cenas"], 1)) or "—"
        partes.append(
            f"\n## {a['id']} — {a['angulo']}\n\n### Hooks (primeiros 3 segundos)\n\n{hooks}\n\n"
            f"### Corpo\n\n{a['corpo']}\n\n### Final (CTA falado)\n\n{a['cta_falado']}\n\n"
            f"### Cenas sugeridas\n\n{cenas}\n\n### Texto do anúncio\n\n{a['texto_principal']}\n\n"
            f"- **Título:** {a['titulo']}\n- **Botão:** {a['cta']}\n{_avisos_md(a)}")
    return "".join(partes)


def linhas_plano(anuncios: list[dict]) -> list[list]:
    linhas = []
    for a in anuncios:
        if a["formato"] == "estatico":
            linhas.append([a["id"], a["angulo"], "Estático", f"{a['id']}-1x1.jpg / {a['id']}-9x16.jpg",
                           "Aberto (Advantage+)", "", "A testar", ""])
        else:
            for n, h in enumerate(a["hooks"], 1):
                linhas.append([a["id"], a["angulo"], "Vídeo", f"Hook {n}: {h}", "Aberto (Advantage+)", "",
                               "A testar", ""])
    return [[_seguro(c) for c in linha] for linha in linhas]


def _gravar(destino_arq: Path, texto: str) -> Path:
    tmp = destino_arq.with_name(f".{destino_arq.name}.tmp")
    tmp.write_text(texto, encoding="utf-8")
    os.replace(tmp, destino_arq)
    return destino_arq


def exportar(pasta_projeto: Path) -> dict:
    pasta_projeto = Path(pasta_projeto).resolve()
    pasta = pasta_projeto / "anuncios"
    anuncios = ler_anuncios(pasta)
    link = destino(pasta_projeto)
    r = {"textos": _gravar(pasta / "textos.md", textos_md(anuncios, link, pasta / "criativos")), "roteiros": None}
    roteiros = roteiros_md(anuncios)
    if roteiros:
        r["roteiros"] = _gravar(pasta / "roteiros.md", roteiros)
    linhas = linhas_plano(anuncios)
    if gerar_xlsx is not None:
        r["plano"] = gerar_xlsx([{"nome": "Plano de teste", "colunas": COLUNAS, "linhas": linhas,
                                  "larguras": [18, 28, 10, 40, 22, 18, 12, 30]}], pasta / "plano-de-teste.xlsx")
    else:
        buf = io.StringIO()
        csv.writer(buf).writerows([COLUNAS] + linhas)
        r["plano"] = _gravar(pasta / "plano-de-teste.csv", "﻿" + buf.getvalue())
    r["link"] = link
    return r


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Exporta textos, roteiros e plano de teste dos anúncios.")
    ap.add_argument("--projeto", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    try:
        r = exportar(Path(args.projeto))
    except KeyboardInterrupt:
        print("Cancelado.", file=sys.stderr)
        return 130
    except ValueError as err:
        print(f"❌ {err}", file=sys.stderr)
        return 1
    except OSError as err:
        print(f"❌ Não consegui gravar os arquivos dos anúncios ({type(err).__name__}).", file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001
        _registrar_log(traceback.format_exc())
        print("❌ Algo deu errado ao exportar os anúncios. Detalhes no log da Máquina (~/.maquina/log).",
              file=sys.stderr)
        return 1
    print(f"✅ Textos: {r['textos']}")
    if r["roteiros"]:
        print(f"✅ Roteiros: {r['roteiros']}")
    print(f"✅ Plano de teste: {r['plano']}")
    if not r["link"]:
        print("⚠️ A página ainda não tem endereço salvo — publique no Sistema 02 e rode de novo pra preencher o link.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
