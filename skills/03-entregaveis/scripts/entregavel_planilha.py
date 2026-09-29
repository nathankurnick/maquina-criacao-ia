# skills/03-entregaveis/scripts/entregavel_planilha.py
"""Gera planilhas .xlsx (planner, controle, calculadora) sem biblioteca externa.

Uso: python entregavel_planilha.py --pasta <pasta do entregável>
Lê <pasta>/planilha.json: {"abas": [{"nome", "colunas", "linhas", "larguras"?}]}
"""
import argparse
import json
import math
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml"
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")  # caracteres proibidos em XML 1.0


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando incompleto ({message}). Use: entregavel_planilha.py --pasta <pasta do entregável>",
              file=sys.stderr)
        raise SystemExit(1)


def _coluna(n: int) -> str:
    letras = ""
    while n:
        n, resto = divmod(n - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _nome_aba(nome: str, usados: set) -> str:
    base = re.sub(r"[\[\]:*?/\\]", "", str(nome or "Planilha")).strip()[:31] or "Planilha"
    base = re.sub(r"\s+", " ", base)
    candidato, n = base, 2
    while candidato.lower() in usados:
        sufixo = f" ({n})"
        candidato = base[:31 - len(sufixo)] + sufixo
        n += 1
    usados.add(candidato.lower())
    return candidato


def _celula(ref: str, valor, estilo: str = "") -> str:
    s = f' s="{estilo}"' if estilo else ""
    if valor is None or valor == "":
        return ""
    if isinstance(valor, bool):
        valor = "Sim" if valor else "Não"
    if isinstance(valor, (int, float)) and math.isfinite(valor):
        return f'<c r="{ref}"{s}><v>{valor}</v></c>'
    texto = _CTRL.sub("", str(valor))
    if texto.startswith("=") and len(texto) > 1:
        return f'<c r="{ref}"{s}><f>{escape(texto[1:])}</f></c>'
    return f'<c r="{ref}" t="inlineStr"{s}><is><t xml:space="preserve">{escape(texto)}</t></is></c>'


def _planilha(aba: dict) -> str:
    colunas = [str(c) for c in aba.get("colunas") or []]
    linhas = [colunas] + [list(l) for l in aba.get("linhas") or []]
    larguras = aba.get("larguras") or [max(10, min(50, len(c) + 4)) for c in colunas]
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
                   for i, w in enumerate(larguras, 1) if isinstance(w, (int, float)))
    rows = []
    for r, linha in enumerate(linhas, 1):
        cels = "".join(_celula(f"{_coluna(c)}{r}", v, "1" if r == 1 else "") for c, v in enumerate(linha, 1))
        rows.append(f'<row r="{r}">{cels}</row>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="{_MAIN}">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
            'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            f'{"<cols>" + cols + "</cols>" if cols else ""}<sheetData>{"".join(rows)}</sheetData></worksheet>')


def gerar_xlsx(abas: list[dict], destino: Path) -> Path:
    usados: set = set()
    nomes = [_nome_aba(a.get("nome"), usados) for a in abas]
    n = len(abas)
    tipos = "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="{_CT}.worksheet+xml"/>'
                    for i in range(1, n + 1))
    content_types = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.'
                     'openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType='
                     '"application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" '
                     f'ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="{_CT}'
                     f'.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="{_CT}.styles+xml"/>'
                     f"{tipos}</Types>")
    rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="{_PKG}">'
            f'<Relationship Id="rId1" Type="{_REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    sheets = "".join(f'<sheet name="{escape(nome, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>'
                     for i, nome in enumerate(nomes, 1))
    workbook = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="{_MAIN}" '
                f'xmlns:r="{_REL}"><sheets>{sheets}</sheets></workbook>')
    wb_rels = "".join(f'<Relationship Id="rId{i}" Type="{_REL}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                      for i in range(1, n + 1))
    wb_rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="{_PKG}">'
               f'{wb_rels}<Relationship Id="rId{n + 1}" Type="{_REL}/styles" Target="styles.xml"/></Relationships>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet xmlns="{_MAIN}">'
              '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/>'
              '<name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/>'
              '</fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border>'
              '<left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf '
              'numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf '
              'numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" '
              'fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle '
              'name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    try:
        _gravar(tmp, abas, content_types, rels, workbook, wb_rels, styles)
        tmp.replace(destino)
    finally:
        tmp.unlink(missing_ok=True)
    return destino


def _gravar(tmp, abas, content_types, rels, workbook, wb_rels, styles) -> None:
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles)
        for i, aba in enumerate(abas, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _planilha(aba))


def ler_planilha_json(pasta: Path) -> list[dict]:
    arq = Path(pasta) / "planilha.json"
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ValueError(f"Não achei {arq}. Escreva as abas da planilha antes.") from err
    except UnicodeDecodeError as err:
        raise ValueError(f"O {arq} não está em UTF-8. Salve o arquivo em UTF-8.") from err
    except (OSError, ValueError) as err:
        raise ValueError(f"O {arq} tem um erro de formatação ({type(err).__name__}).") from err
    abas = dados.get("abas") if isinstance(dados, dict) else None
    if not isinstance(abas, list) or not abas:
        raise ValueError(f"O {arq} precisa ter pelo menos uma aba em \"abas\".")
    for aba in abas:
        if not isinstance(aba, dict) or not isinstance(aba.get("colunas"), list):
            raise ValueError(f"Cada aba do {arq} precisa de \"colunas\" (lista de nomes).")
        if not isinstance(aba.get("linhas", []), list):
            raise ValueError(f"As \"linhas\" de cada aba do {arq} precisam ser uma lista.")
    return abas


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Gera a planilha .xlsx do entregável.")
    ap.add_argument("--pasta", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    pasta = Path(args.pasta).resolve()
    try:
        arq = gerar_xlsx(ler_planilha_json(pasta), pasta / f"{pasta.name}.xlsx")
    except KeyboardInterrupt:
        print("Cancelado.", file=sys.stderr)
        return 130
    except ValueError as err:
        print(f"❌ {err}", file=sys.stderr)
        return 1
    except OSError as err:
        print(f"❌ Não consegui gravar a planilha em {pasta} ({type(err).__name__}).", file=sys.stderr)
        return 1
    print(f"✅ Planilha pronta: {arq}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
