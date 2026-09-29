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
for arg in "$@"; do [ "$arg" = "--sem-chaves" ] && SEM_CHAVES=1; done

falhar() { printf '\n❌ %s\n' "$1" >&2; exit 1; }

echo "🤖 Instalando a Máquina Criação IA..."

command -v claude >/dev/null 2>&1 \
  || falhar "Não achei o Claude Code. Instale primeiro (https://claude.com/claude-code) e rode este instalador de novo."

PY=""
for c in python3.13 python3.12 python3.11 python3.10 \
         /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 \
         /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 \
     && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$(command -v "$c")"; break
  fi
done
[ -n "$PY" ] || falhar "Precisa do Python 3.10 ou mais novo. No Mac: instale o Homebrew (https://brew.sh), rode 'brew install python@3.12' e depois este instalador de novo."

mkdir -p "$MAQUINA_HOME"
chmod 700 "$MAQUINA_HOME"

if [ ! -x "$MAQUINA_HOME/venv/bin/python" ]; then
  "$PY" -m venv "$MAQUINA_HOME/venv" || falhar "Não consegui criar o ambiente Python em $MAQUINA_HOME/venv."
fi

if [ "${MAQUINA_PULAR_DEPS:-0}" != "1" ]; then
  echo "📦 Instalando dependências (pode levar alguns minutos)..."
  "$MAQUINA_HOME/venv/bin/python" -m pip install -q --upgrade pip \
    && "$MAQUINA_HOME/venv/bin/python" -m pip install -q -r "$AQUI/requirements.txt" \
    || falhar "Falhou ao instalar as dependências. Confira sua internet e rode de novo."
  echo "🌐 Baixando o navegador usado na pesquisa de ofertas..."
  "$MAQUINA_HOME/venv/bin/python" -m playwright install chromium \
    || falhar "Falhou ao baixar o navegador. Confira sua internet e rode de novo."
fi

rm -rf "$MAQUINA_HOME/nucleo"
cp -R "$AQUI/nucleo" "$MAQUINA_HOME/nucleo"
find "$MAQUINA_HOME/nucleo" -name __pycache__ -prune -exec rm -rf {} +
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
  "$BIN_DIR/maquina" chaves
fi

echo
echo "✅ Máquina Criação IA instalada! Abra um terminal novo, rode 'claude' e digite /01-pesquisa-ofertas pra começar."
