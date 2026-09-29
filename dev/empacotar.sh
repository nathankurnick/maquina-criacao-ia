#!/usr/bin/env bash
# Gera dist/maquina-criacao-ia-<versão>.zip — o arquivo que vai pra área de membros.
# Uso: bash dev/empacotar.sh [--sem-pdf]
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
VERSAO="$(tr -d '[:space:]' < "$RAIZ/VERSION")"
NOME="maquina-criacao-ia-$VERSAO"
DIST="$RAIZ/dist"
PACOTE="$DIST/pacote/$NOME"
ZIP="$DIST/$NOME.zip"
COM_PDF=1
for arg in "$@"; do
  case "$arg" in
    --sem-pdf) COM_PDF=0 ;;
    *) echo "Opção desconhecida: $arg" >&2; exit 1 ;;
  esac
done

PY="$RAIZ/.venv/bin/python"; [ -x "$PY" ] || PY=python3
falhar() { echo "❌ $1" >&2; exit 1; }

rm -rf "$DIST/pacote" "$ZIP"
mkdir -p "$PACOTE"

for item in instalar.sh "Instalar Máquina.command" LEIA-ME.txt VERSION requirements.txt bin nucleo skills; do
  [ -e "$RAIZ/$item" ] || falhar "Faltou $item no repositório."
  rsync -a --exclude __pycache__ --exclude .DS_Store --exclude .pytest_cache "$RAIZ/$item" "$PACOTE/"
done

if [ "$COM_PDF" = "1" ]; then
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  cp -R "$RAIZ/docs-aluno/como-instalar" "$TMP/como-instalar"
  MAQUINA_HOME="$RAIZ" "$RAIZ/.venv/bin/python" "$RAIZ/skills/03-entregaveis/scripts/entregavel_pdf.py" \
    --pasta "$TMP/como-instalar" --paleta azul-laranja \
    || falhar "Não consegui gerar o COMO-INSTALAR.pdf."
  cp "$TMP/como-instalar/como-instalar.pdf" "$PACOTE/COMO-INSTALAR.pdf"
fi

[ "$COM_PDF" = "1" ] || echo "⚠️ Pacote sem o COMO-INSTALAR.pdf (só pra teste)"
chmod +x "$PACOTE/instalar.sh" "$PACOTE/Instalar Máquina.command" "$PACOTE/bin/maquina"

# Python (e não o comando zip) pra gravar os nomes em UTF-8 — "Instalar Máquina.command" tem acento —
# guardando as permissões Unix de cada arquivo.
"$PY" - "$DIST/pacote" "$NOME" "$ZIP" <<'PY'
import os, sys, unicodedata, zipfile
base, nome, destino = sys.argv[1:4]
with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
    for pasta, dirs, arquivos in os.walk(os.path.join(base, nome)):
        dirs.sort()
        for item in sorted(dirs) + sorted(arquivos):
            caminho = os.path.join(pasta, item)
            rel = unicodedata.normalize("NFC", os.path.relpath(caminho, base))
            info = zipfile.ZipInfo(rel + ("/" if os.path.isdir(caminho) else ""))
            info.external_attr = (os.stat(caminho).st_mode & 0xFFFF) << 16
            info.date_time = (2026, 1, 1, 0, 0, 0)
            if os.path.isdir(caminho):
                z.writestr(info, b"")
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(caminho, "rb") as f:
                    z.writestr(info, f.read())
PY

PROIBIDOS="$("$PY" -c 'import sys,zipfile; print("\n".join(zipfile.ZipFile(sys.argv[1]).namelist()))' "$ZIP" | grep -E '(^|/)(tests|\.venv|__pycache__|dev|docs-aluno|log|\.pytest_cache)(/|$)|\.DS_Store|requirements-dev\.txt|pytest\.ini|(^|/)\.env$|(^|/)chaves\.env$|\.log$' || true)"
if [ -n "$PROIBIDOS" ]; then
  rm -f "$ZIP"
  falhar "O zip ficou com arquivos que não podem ir pro aluno: $PROIBIDOS"
fi
rm -rf "$DIST/pacote"
echo "✅ Pacote pronto: $ZIP"
