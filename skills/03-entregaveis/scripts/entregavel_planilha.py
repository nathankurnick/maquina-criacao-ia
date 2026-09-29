# skills/03-entregaveis/scripts/entregavel_planilha.py
"""Gera planilhas .xlsx (planner, controle, calculadora) sem biblioteca externa.

Uso: python entregavel_planilha.py --pasta <pasta do entregável>
Lê <pasta>/planilha.json: {"abas": [{"nome", "colunas", "linhas", "larguras"?, "formatos"?}]}
Fórmulas em inglês e com vírgula (=SUM(C2:C31)); "formatos" por coluna: texto, numero, moeda, percentual, data.
"""
import argparse
import json
import datetime
import math
import os
import re
import sys
import traceback
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml"
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")  # caracteres proibidos em XML 1.0
# formato -> (numFmtId, código customizado ou None)
_FORMATOS = {"texto": (49, None), "numero": (4, None), "moeda": (164, '"R$" #,##0.00'),
             "percentual": (9, None), "data": (165, "dd/mm/yyyy")}
_PT_PARA_EN = {"SOMASE": "SUMIF", "SOMA": "SUM", "SE": "IF", "PROCV": "VLOOKUP", "MÉDIA": "AVERAGE",
               "MEDIA": "AVERAGE", "CONT.SE": "COUNTIF"}
_PT_FUNC = re.compile(r"(?<![A-Za-z0-9_.])(SOMASE|SOMA|SE|PROCV|MÉDIA|MEDIA|CONT\.SE)\s*\(", re.I)
_EXCEL_ZERO = datetime.date(1899, 12, 30)


def _log_erro(texto: str) -> None:
    """Grava no log da Máquina só com a biblioteca padrão; nunca levanta erro."""
    try:
        pasta = Path(os.environ.get("MAQUINA_HOME") or os.path.expanduser("~/.maquina")) / "log"
        pasta.mkdir(parents=True, exist_ok=True)
        with (pasta / "maquina.log").open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {texto}\n")
    except Exception:  # noqa: BLE001
        pass


def _serial_data(txt) -> "int | None":
    """'2026-10-01' -> número de série do Excel; None se não for ISO; ValueError se data impossível."""
    if isinstance(txt, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", txt.strip()):
        return (datetime.date.fromisoformat(txt.strip()) - _EXCEL_ZERO).days
    return None


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
    base = re.sub(r"[\[\]:*?/\\]", "", _CTRL.sub("", str(nome or "Planilha")))
    base = re.sub(r"\s+", " ", base).strip().strip("'").strip()[:31].strip("'").strip() or "Planilha"
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


def _planilha(aba: dict, estilos: "dict | None" = None) -> str:
    estilos = estilos or {}
    colunas = [str(c) for c in aba.get("colunas") or []]
    formatos = [f for f in aba.get("formatos") or []]
    linhas = [colunas] + [list(l) for l in aba.get("linhas") or []]
    larguras = aba.get("larguras") or [max(10, min(50, len(c) + 4)) for c in colunas]
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
                   for i, w in enumerate(larguras, 1) if isinstance(w, (int, float)))
    rows = []
    for r, linha in enumerate(linhas, 1):
        cels = []
        for c, v in enumerate(linha, 1):
            fmt = formatos[c - 1] if r > 1 and c <= len(formatos) else None
            if fmt == "data" and _serial_data(v) is not None:
                v = _serial_data(v)
            estilo = "1" if r == 1 else str(estilos[fmt]) if fmt in estilos else ""
            cels.append(_celula(f"{_coluna(c)}{r}", v, estilo))
        rows.append(f'<row r="{r}">{"".join(cels)}</row>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="{_MAIN}">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
            'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            f'{"<cols>" + cols + "</cols>" if cols else ""}<sheetData>{"".join(rows)}</sheetData></worksheet>')


def gerar_xlsx(abas: list[dict], destino: Path) -> Path:
    usados: set = set()
    usados_fmt = [f for f in _FORMATOS if any(f in (a.get("formatos") or []) for a in abas)]
    estilos = {f: 2 + i for i, f in enumerate(usados_fmt)}  # 0 normal, 1 cabeçalho, 2+ formatos
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
                f'xmlns:r="{_REL}"><sheets>{sheets}</sheets><calcPr fullCalcOnLoad="1"/></workbook>')
    wb_rels = "".join(f'<Relationship Id="rId{i}" Type="{_REL}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                      for i in range(1, n + 1))
    wb_rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="{_PKG}">'
               f'{wb_rels}<Relationship Id="rId{n + 1}" Type="{_REL}/styles" Target="styles.xml"/></Relationships>')
    custom = [(i, c) for i, c in (_FORMATOS[f] for f in usados_fmt) if c]
    numfmts = (f'<numFmts count="{len(custom)}">' + "".join(
        f'<numFmt numFmtId="{i}" formatCode="{escape(c, {chr(34): "&quot;"})}"/>' for i, c in custom)
        + "</numFmts>") if custom else ""
    xfs_fmt = "".join(f'<xf numFmtId="{_FORMATOS[f][0]}" fontId="0" fillId="0" borderId="0" xfId="0" '
                      'applyNumberFormat="1"/>' for f in usados_fmt)
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<styleSheet xmlns="{_MAIN}">'
              f'{numfmts}<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/>'
              '<name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/>'
              '</fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border>'
              '<left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf '
              'numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="' + str(2 + len(usados_fmt)) + '"><xf '
              'numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" '
              'fillId="0" borderId="0" xfId="0" applyFont="1"/>' + xfs_fmt + '</cellXfs><cellStyles count="1"><cellStyle '
              'name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    try:
        _gravar(tmp, abas, content_types, rels, workbook, wb_rels, styles, estilos)
        tmp.replace(destino)
    finally:
        tmp.unlink(missing_ok=True)
    return destino


def _gravar(tmp, abas, content_types, rels, workbook, wb_rels, styles, estilos) -> None:
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles)
        for i, aba in enumerate(abas, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _planilha(aba, estilos))


def _validar_formula(texto: str, ref: str, nome: str) -> None:
    sem_aspas = re.sub(r'"[^"]*"', '""', texto)
    achou = _PT_FUNC.search(sem_aspas)
    if achou:
        pt = achou.group(1).upper()
        en = _PT_PARA_EN[pt.replace("É", "E") if pt not in _PT_PARA_EN else pt]
        raise ValueError(f'A fórmula da célula {ref} (aba "{nome}") usa o nome em português {achou.group(1)}(…). '
                         f"Use o nome em inglês, que funciona em qualquer Excel: {en}(…).")
    if ";" in sem_aspas:
        raise ValueError(f'A fórmula da célula {ref} (aba "{nome}") usa ponto e vírgula. Use vírgula entre os '
                         "argumentos, por exemplo =IF(A2>0,1,0).")


def _validar_aba(aba: dict, arq) -> None:
    nome = str(aba.get("nome") or "Planilha")
    linhas = aba.get("linhas", [])
    if not isinstance(linhas, list):
        raise ValueError(f"As \"linhas\" de cada aba do {arq} precisam ser uma lista.")
    larguras = aba.get("larguras")
    if larguras is not None and (not isinstance(larguras, list) or not all(
            isinstance(w, (int, float)) and not isinstance(w, bool) and w > 0 for w in larguras)):
        raise ValueError(f'As "larguras" da aba "{nome}" precisam ser uma lista de números, como [12, 30, 15].')
    formatos = aba.get("formatos")
    if formatos is not None:
        if not isinstance(formatos, list):
            raise ValueError(f'Os "formatos" da aba "{nome}" precisam ser uma lista, como ["texto", "moeda"].')
        for f in formatos:
            if f not in _FORMATOS:
                raise ValueError(f'Formato "{f}" não existe (aba "{nome}"). Use: {", ".join(_FORMATOS)}.')
    formatos = formatos or []
    for r, linha in enumerate(linhas, 2):
        if not isinstance(linha, list):
            raise ValueError(f'A linha {r - 1} da aba "{nome}" precisa ser uma lista de valores, '
                             'como ["Seg", "Omelete", 420].')
        for c, v in enumerate(linha, 1):
            ref = f"{_coluna(c)}{r}"
            if isinstance(v, str) and v.startswith("=") and len(v) > 1:
                _validar_formula(v, ref, nome)
            if c <= len(formatos) and formatos[c - 1] == "data" and isinstance(v, str) and v.strip():
                try:
                    if _serial_data(v) is None:
                        raise ValueError
                except ValueError:
                    raise ValueError(f'A data da célula {ref} (aba "{nome}") não é válida. '
                                     'Use o formato "2026-10-01" (ano-mês-dia) ou o número de série do Excel.') from None


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
        _validar_aba(aba, arq)
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
    except Exception:  # noqa: BLE001 — nunca mostra traceback ao aluno
        _log_erro(traceback.format_exc())
        print("❌ Algo deu errado ao gerar a planilha. Detalhes no log da Máquina (~/.maquina/log).",
              file=sys.stderr)
        return 1
    print(f"✅ Planilha pronta: {arq}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
