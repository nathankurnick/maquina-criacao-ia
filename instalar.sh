#!/usr/bin/env bash
# Instalador da Máquina Criação IA. Pode rodar de novo pra atualizar:
# chaves (~/.maquina/chaves.env) e projetos (~/MaquinaIA) são preservados.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
MAQUINA_HOME="${MAQUINA_HOME:-$HOME/.maquina}"
BIN_DIR="${MAQUINA_BIN:-$HOME/.local/bin}"
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
export MAQUINA_HOME

SEM_CHAVES=0
for arg in "$@"; do
  case "$arg" in
    --sem-chaves) SEM_CHAVES=1 ;;
    *) echo "⚠️ Opção desconhecida: $arg (ignorada)" >&2 ;;
  esac
done

LOG="$MAQUINA_HOME/log/instalacao.log"
falhar() { printf '\n❌ %s\n' "$1" >&2; exit 1; }
falhar_log() { falhar "$1 Detalhes em: $LOG"; }

echo "🤖 Instalando a Máquina Criação IA..."

command -v claude >/dev/null 2>&1 \
  || falhar "Não achei o Claude Code. Instale primeiro (https://claude.com/claude-code) e rode este instalador de novo."

# Nunca roda /usr/bin/python3: num Mac sem as Command Line Tools ele abre um popup de instalação do Xcode.
PY_DIRS="${MAQUINA_PY_DIRS-/opt/homebrew/bin /usr/local/bin}"
candidatos=(python3.13 python3.12 python3.11 python3.10)
for d in $PY_DIRS; do
  for v in 3.13 3.12 3.11 3.10; do candidatos+=("$d/python$v"); done
done
candidatos+=(python3)

PY=""
for c in "${candidatos[@]}"; do
  achado="$(command -v "$c" 2>/dev/null || true)"
  [ -n "$achado" ] || continue
  [ "$achado" = "/usr/bin/python3" ] && continue
  if "$achado" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$achado"; break
  fi
done
[ -n "$PY" ] || falhar "Precisa do Python 3.10 ou mais novo. No Mac: instale o Homebrew (https://brew.sh), rode 'brew install python@3.12' e depois este instalador de novo."

mkdir -p "$MAQUINA_HOME/log"
chmod 700 "$MAQUINA_HOME"

# venv existente mas velho/quebrado: recria
if [ -e "$MAQUINA_HOME/venv" ] \
   && ! "$MAQUINA_HOME/venv/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  rm -rf "$MAQUINA_HOME/venv"
fi
if [ ! -x "$MAQUINA_HOME/venv/bin/python" ]; then
  "$PY" -m venv "$MAQUINA_HOME/venv" >>"$LOG" 2>&1 || falhar_log "Não consegui criar o ambiente Python."
fi

if [ "${MAQUINA_PULAR_DEPS:-0}" != "1" ]; then
  echo "📦 Instalando dependências (pode levar alguns minutos)..."
  { "$MAQUINA_HOME/venv/bin/python" -m pip install -q --upgrade pip \
    && "$MAQUINA_HOME/venv/bin/python" -m pip install -q -r "$AQUI/requirements.txt"; } >>"$LOG" 2>&1 \
    || falhar_log "Falhou ao instalar as dependências. Confira sua internet e rode de novo."
  echo "🌐 Baixando o navegador usado na pesquisa de ofertas..."
  "$MAQUINA_HOME/venv/bin/python" -m playwright install chromium >>"$LOG" 2>&1 \
    || falhar_log "Falhou ao baixar o navegador. Confira sua internet e rode de novo."
fi

# troca atômica: uma cópia falha nunca deixa a instalação sem núcleo
rm -rf "$MAQUINA_HOME/nucleo.novo"
cp -R "$AQUI/nucleo" "$MAQUINA_HOME/nucleo.novo" || falhar "Não consegui copiar os arquivos da máquina."
find "$MAQUINA_HOME/nucleo.novo" -name __pycache__ -prune -exec rm -rf {} +
rm -rf "$MAQUINA_HOME/nucleo"
mv "$MAQUINA_HOME/nucleo.novo" "$MAQUINA_HOME/nucleo"
cp "$AQUI/VERSION" "$MAQUINA_HOME/VERSION"

mkdir -p "$SKILLS_DIR"
for pasta in "$AQUI"/skills/*/; do
  [ -f "${pasta}SKILL.md" ] || continue
  nome="$(basename "$pasta")"
  rm -rf "$SKILLS_DIR/$nome"
  cp -R "$pasta" "$SKILLS_DIR/$nome"
  echo "   ✔ skill /$nome"
done

mkdir -p "$BIN_DIR"
cp "$AQUI/bin/maquina" "$BIN_DIR/maquina"
chmod +x "$BIN_DIR/maquina"
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) grep -qs 'MAQUINA_BIN_PATH' "$HOME/.zshrc" \
       || printf '\nexport PATH="%s:$PATH" # MAQUINA_BIN_PATH\n' "$BIN_DIR" >> "$HOME/.zshrc" ;;
esac

if [ "$SEM_CHAVES" = "0" ]; then
  echo
  echo "Agora as chaves de API (todas opcionais — dá pra configurar depois com: maquina chaves)"
  "$BIN_DIR/maquina" chaves \
    || echo "Sem problema: dá pra configurar as chaves depois com: maquina chaves"
fi

echo
echo "✅ Máquina Criação IA instalada! Abra um terminal novo, rode 'claude' e digite /01-pesquisa-ofertas pra começar."
