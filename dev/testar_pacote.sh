#!/usr/bin/env bash
# Teste ponta a ponta do zip do aluno: instala num HOME temporário (pip e Chromium de verdade)
# e roda um produto de exemplo pelos Sistemas 01 (só o offline), 02, 03, 04 e 05 usando SÓ o que
# foi instalado em $HOME_TMP/.maquina e $HOME_TMP/.claude/skills, com os comandos dos SKILL.md.
# Uso: bash dev/testar_pacote.sh dist/maquina-criacao-ia-<versão>.zip
#      MANTER=1 bash dev/testar_pacote.sh <zip>   # não apaga o diretório temporário no fim
#      NAVEGADOR_DO_CACHE=1 bash dev/testar_pacote.sh <zip>
#        # copia o Chromium já baixado (~/Library/Caches/ms-playwright) pro HOME temporário, então o
#        # "playwright install chromium" do instalador só confere e não baixa nada. Só pra máquina sem
#        # acesso ao CDN do Playwright: o teste de lançamento é SEM esta opção (download de verdade).
set -euo pipefail

[ $# -eq 1 ] || { echo "Uso: bash dev/testar_pacote.sh <zip>" >&2; exit 1; }
[ -f "$1" ] || { echo "❌ Não achei o zip: $1" >&2; exit 1; }
ZIP="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
HOME_REAL="$HOME"

# Nada do ambiente de quem roda o teste pode vazar pra instalação temporária.
unset MAQUINA_HOME MAQUINA_BIN MAQUINA_PROJETOS MAQUINA_PULAR_DEPS MAQUINA_SKILLS_SRC MAQUINA_PY_DIRS \
      CLAUDE_SKILLS_DIR PLAYWRIGHT_BROWSERS_PATH PYTHONPATH PYTHONHOME VIRTUAL_ENV \
      KIE_API_KEY NETLIFY_TOKEN PIP_REQUIRE_VIRTUALENV

TMP_BASE="${TMPDIR:-/tmp}"
TMP="$(mktemp -d "${TMP_BASE%/}/maquina-teste.XXXXXX")"
HOME_TMP="$TMP/home"
mkdir -p "$HOME_TMP/Downloads"
case "$HOME_TMP" in
  "$HOME_REAL"|"$HOME_REAL/.maquina"*|"$HOME_REAL/.claude"*|"$HOME_REAL/MaquinaIA"*)
    echo "❌ O HOME temporário caiu dentro do HOME real ($HOME_TMP). Abortando." >&2; exit 1 ;;
esac

limpar() {
  if [ "${MANTER:-0}" = "1" ]; then
    echo "📁 Diretório temporário mantido (MANTER=1): $TMP"
  else
    rm -rf "$TMP"
  fi
}
trap limpar EXIT

# "Carimbo" do ~ real (instalação, skills e projetos): não pode mudar durante o teste.
carimbo_real() {
  local alvo
  for alvo in "$HOME_REAL/.maquina" "$HOME_REAL/.claude/skills" "$HOME_REAL/MaquinaIA" "$HOME_REAL/.local/bin/maquina"; do
    if [ -e "$alvo" ]; then
      printf '%s %s\n' "$alvo" "$(find "$alvo" -maxdepth 2 -exec stat -f '%N %m %z' {} + 2>/dev/null | shasum | cut -c1-12)"
    else
      printf '%s ausente\n' "$alvo"
    fi
  done
}
CARIMBO_ANTES="$(carimbo_real)"

PY="$HOME_TMP/.maquina/venv/bin/python"
M="$HOME_TMP/bin/maquina"
SK="$HOME_TMP/.claude/skills"
S1="$SK/01-pesquisa-ofertas/scripts"
S2="$SK/02-pagina-de-vendas/scripts"
S3="$SK/03-entregaveis/scripts"
S4="$SK/04-anuncios/scripts"
S5="$SK/05-funil/scripts"
SAIDA="$TMP/saida-do-passo.txt"
FALHAS=()

# Roda um comando "como o aluno": HOME e MAQUINA_HOME temporários, maquina temporária no PATH.
aluno() {
  env HOME="$HOME_TMP" MAQUINA_HOME="$HOME_TMP/.maquina" PATH="$HOME_TMP/bin:$PATH" "$@"
}

passo() { printf '\n▶ %s\n' "$*"; }

# espera_saida <código> <comando…>: roda como aluno e confere o código de saída.
espera_saida() {
  local esperado="$1"; shift
  local codigo=0
  aluno "$@" >"$SAIDA" 2>&1 || codigo=$?
  sed 's/^/    │ /' "$SAIDA" | tail -n 25
  if [ "$codigo" = "$esperado" ]; then
    echo "    ✔ saiu $codigo"
  else
    echo "    ✘ saiu $codigo (esperado $esperado)"
    FALHAS+=("$(basename "$1") $(basename "${2:-}") ${3:-}: saiu $codigo, esperado $esperado")
  fi
}

falha() { echo "    ✘ $1"; FALHAS+=("$1"); }
ok() { echo "    ✔ $1"; }

passo "Descompactando o zip ($(basename "$ZIP"))"
( cd "$HOME_TMP/Downloads" && ditto -x -k "$ZIP" . )
PKG="$(find "$HOME_TMP/Downloads" -mindepth 1 -maxdepth 1 -type d -name 'maquina-criacao-ia-*' | head -1)"
[ -n "$PKG" ] || { echo "❌ O zip não tem a pasta maquina-criacao-ia-<versão>." >&2; exit 1; }
VERSAO="$(tr -d '[:space:]' < "$PKG/VERSION")"
ok "pasta $(basename "$PKG") (versão $VERSAO)"
for arq in "Instalar Máquina.command" instalar.sh bin/maquina; do
  [ -x "$PKG/$arq" ] && ok "$arq é executável" || falha "$arq não é executável depois de descompactar"
done
[ -f "$PKG/COMO-INSTALAR.pdf" ] && ok "COMO-INSTALAR.pdf presente" || falha "Faltou COMO-INSTALAR.pdf no zip"

if [ "${NAVEGADOR_DO_CACHE:-0}" = "1" ]; then
  passo "NAVEGADOR_DO_CACHE=1: copiando o Chromium já baixado pro HOME temporário (sem download)"
  CACHE_REAL="$HOME_REAL/Library/Caches/ms-playwright"
  [ -d "$CACHE_REAL" ] || { echo "❌ Não achei $CACHE_REAL." >&2; exit 1; }
  mkdir -p "$HOME_TMP/Library/Caches"
  cp -cR "$CACHE_REAL" "$HOME_TMP/Library/Caches/ms-playwright" 2>/dev/null \
    || cp -R "$CACHE_REAL" "$HOME_TMP/Library/Caches/ms-playwright"
  ok "cópia em $HOME_TMP/Library/Caches/ms-playwright (o ~ real só foi lido)"
  echo "    ⚠️ Este modo NÃO testa o download do Chromium: rode sem NAVEGADOR_DO_CACHE antes de lançar."
fi

passo "Instalando com HOME temporário (pip e Chromium de verdade; alguns minutos)"
codigo=0
env HOME="$HOME_TMP" MAQUINA_HOME="$HOME_TMP/.maquina" MAQUINA_BIN="$HOME_TMP/bin" \
    CLAUDE_SKILLS_DIR="$SK" bash "$PKG/instalar.sh" --sem-chaves >"$SAIDA" 2>&1 || codigo=$?
sed 's/^/    │ /' "$SAIDA"
if [ "$codigo" != "0" ]; then
  echo "    ✘ instalador saiu $codigo"
  [ -f "$HOME_TMP/.maquina/log/instalacao.log" ] && tail -n 30 "$HOME_TMP/.maquina/log/instalacao.log"
  echo; echo "❌ Pacote reprovado: a instalação falhou."; exit 1
fi
ok "instalador saiu 0"
for s in 01-pesquisa-ofertas 02-pagina-de-vendas 03-entregaveis 04-anuncios 05-funil; do
  [ -f "$SK/$s/SKILL.md" ] || falha "skill $s não foi instalada"
done
[ -x "$M" ] || { echo "❌ O comando maquina não foi instalado em $M." >&2; exit 1; }
[ -z "$(find "$HOME_TMP/.maquina/nucleo" "$SK" -name __pycache__ -o -name '*.pyc' | head -1)" ] \
  && ok "sem __pycache__ na instalação" || falha "instalação veio com __pycache__"

passo "maquina versao / status --json"
espera_saida 0 "$M" versao
[ "$(tr -d '[:space:]' < "$SAIDA")" = "$VERSAO" ] && ok "versão $VERSAO" || falha "maquina versao não imprimiu $VERSAO"
espera_saida 0 "$M" status --json
aluno "$PY" - "$SAIDA" "$VERSAO" <<'PY' && ok "status --json confere" || falha "status --json diferente do esperado"
import json, sys
d = json.load(open(sys.argv[1]))
assert d["versao"] == sys.argv[2], d
assert d["chaves"] == {"KIE_API_KEY": False, "NETLIFY_TOKEN": False}, d
assert d["projetos"] == [], d
PY

# ─────────────────────────────── Projeto e oferta ───────────────────────────────
passo "maquina projeto novo 'Teste Pacote' + oferta"
espera_saida 0 "$M" projeto novo 'Teste Pacote'
P="$(tail -n 1 "$SAIDA")"
SLUG="$(basename "$P")"
[ "$P" = "$HOME_TMP/MaquinaIA/teste-pacote" ] && ok "projeto em $P" || falha "projeto em lugar inesperado: $P"
espera_saida 0 "$M" oferta definir "$SLUG" nome='Marmitas Já' nicho='marmitas fit' \
  avatar='Mulheres de 25 a 45 anos sem tempo de cozinhar' \
  promessa='Comida pronta pra 15 dias cozinhando uma vez por semana' \
  mecanismo='Método Domingo Único' preco='R$ 27,00' garantia='7 dias' \
  link_checkout='https://pay.kiwify.com.br/teste123' paleta='verde-branco'
espera_saida 0 "$M" oferta adicionar "$SLUG" entregaveis 'Guia Marmitas Já'
espera_saida 0 "$M" oferta adicionar "$SLUG" bonus 'Planilha de custos'
espera_saida 0 "$M" oferta adicionar "$SLUG" bonus -- '-50% no combo'
espera_saida 0 "$M" oferta faltando "$SLUG"
[ -z "$(tr -d '[:space:]' < "$SAIDA")" ] && ok "oferta completa" || falha "oferta faltando: $(tr '\n' ' ' < "$SAIDA")"
espera_saida 0 "$M" oferta mostrar "$SLUG"
aluno "$PY" - "$SAIDA" <<'PY' && ok "oferta mostrar confere" || falha "oferta mostrar diferente do gravado"
import json, sys
d = json.load(open(sys.argv[1]))
assert d["preco"] == "R$ 27,00" and d["paleta"] == "verde-branco", d
assert d["bonus"] == ["Planilha de custos", "-50% no combo"], d
assert d["entregaveis"] == ["Guia Marmitas Já"], d
PY

# ─────────────────────────────── 01 (só o offline) ───────────────────────────────
passo "01: ofertas.py num anuncios.json de exemplo + registrar_escolha.py"
B="$P/pesquisa/2026-01-01-marmitas-fit"
mkdir -p "$B"
aluno "$PY" - "$B/anuncios.json" <<'PY'
import json, sys, time
agora = int(time.time())
def ad(i, link, dias, rep, pagina="Marmitas da Ana"):
    return {"id": str(i), "pagina": pagina, "inicio": agora - dias * 86400, "repeticoes": rep,
            "cta": "Saiba mais", "link": link, "titulo": "Marmitas prontas",
            "texto": "Cansada de cozinhar todo dia? Prepare tudo num domingo.",
            "videos": [], "imagens": [], "midia": "nenhuma"}
ads = [ad(i, "https://pay.kiwify.com.br/AbC123", 45, 8) for i in range(1, 5)]
ads += [ad(10, "https://outraloja.com.br/oferta", 3, 1, "Outra Loja")]
json.dump(ads, open(sys.argv[1], "w"), ensure_ascii=False)
PY
espera_saida 0 "$PY" "$S1/ofertas.py" "$B/anuncios.json" --saida "$B"
O="$P/pesquisa/oferta-kiwify-com-br-abc123"
espera_saida 0 "$PY" "$S1/registrar_escolha.py" --busca "$B" --oferta 1 --pasta-oferta "$O"
aluno "$PY" - "$P/pesquisa/escolhida.json" "$O" <<'PY' && ok "escolhida.json confere" || falha "escolhida.json errado"
import json, sys
d = json.load(open(sys.argv[1]))
assert d["chave"] == "kiwify.com.br/AbC123" and d["pasta_oferta"] == sys.argv[2], d
PY

# ─────────────────────────────── 02 Página de vendas ───────────────────────────────
passo "02: conteudo.json mínimo, paleta, montar e publicar sem chave"
mkdir -p "$P/pagina"
cat > "$P/pagina/conteudo.json" <<'JSON'
{
  "hero": {"badge": "MÉTODO PASSO A PASSO",
           "headline": "Comida pronta pra **15 dias** cozinhando uma vez por semana",
           "subheadline": "Receitas testadas, lista de compras e como congelar.",
           "cta": "QUERO MINHAS MARMITAS"},
  "conteudo": {"titulo": "O que você vai encontrar", "subtitulo": "Do básico ao congelamento.",
    "itens": [
      {"icone": "livro", "titulo": "Receitas base", "descricao": "As marmitas que resolvem a semana."},
      {"icone": "lista", "titulo": "Lista de compras", "descricao": "O que comprar e quanto."},
      {"icone": "relogio", "titulo": "Domingo Único", "descricao": "A ordem certa de preparo."},
      {"icone": "calculadora", "titulo": "Custos", "descricao": "Quanto sai cada marmita."},
      {"icone": "escudo", "titulo": "Congelamento", "descricao": "Como guardar sem estragar."}]},
  "bonus": {"titulo": "Bônus de hoje", "subtitulo": "",
            "itens": [{"titulo": "Planilha de custos", "descricao": "Calcule o preço.", "valor": "R$47"}]},
  "planos": {"titulo": "Escolha seu acesso", "subtitulo": "",
    "basico": {"nome": "ACESSO COMPLETO", "itens": ["Guia Marmitas Já", "Planilha de custos"],
               "precoDe": "", "precoPor": "R$ 27,00",
               "checkoutUrl": "https://pay.kiwify.com.br/teste123", "cta": "QUERO MEU ACESSO"},
    "premium": {"ativo": false}},
  "garantia": {"titulo": "GARANTIA INCONDICIONAL", "dias": 7,
               "texto": "Se não gostar, peça o reembolso em até 7 dias.", "cta": "GARANTIR MEU ACESSO"},
  "rodape": {"nomeProduto": "Marmitas Já", "disclaimer": ""}
}
JSON
espera_saida 0 "$PY" "$S2/pagina_config.py" --projeto "$P" --paletas
espera_saida 0 "$PY" "$S2/pagina_config.py" --projeto "$P" --definir 'paleta=verde-branco'
espera_saida 0 "$PY" "$S2/pagina_render.py" --projeto "$P"
grep -q 'pay.kiwify.com.br/teste123' "$P/pagina/site/index.html" 2>/dev/null \
  && ok "checkout na página" || falha "link de checkout não apareceu em pagina/site/index.html"
espera_saida 3 "$PY" "$S2/pagina_publicar.py" --projeto "$P"

# ─────────────────────────────── 03 Entregáveis ───────────────────────────────
passo "03: guia (capa → PDF com carrossel) e planilha"
E="$P/entregaveis/guia-marmitas"
mkdir -p "$E"
cat > "$E/meta.json" <<'JSON'
{"titulo": "Guia Marmitas Já", "subtitulo": "15 dias de comida pronta num domingo", "tipo": "guia", "autor": "Ana Teste"}
JSON
cat > "$E/conteudo.md" <<'MD'
# Como funciona o Domingo Único

Você cozinha uma vez e come bem por 15 dias. Este guia mostra a ordem certa.

## O que você precisa

- Potes de vidro com tampa
- Uma assadeira grande
- Duas panelas

> **Dica:** comece pelos alimentos que demoram mais no forno.

# Lista de compras

| Item | Quantidade |
|------|-----------|
| Arroz | 2 kg |
| Frango | 3 kg |
| Legumes | 4 kg |

- [ ] Separar os potes
- [ ] Temperar o frango na véspera
MD
espera_saida 0 "$PY" "$S3/entregavel_capa.py" --pasta "$E" --paleta 'verde-branco'
espera_saida 0 "$PY" "$S3/entregavel_pdf.py" --pasta "$E" --paleta 'verde-branco' \
  --carrossel "$P/pagina/imagens/carrossel" --ordem 1
E2="$P/entregaveis/planilha-custos"
mkdir -p "$E2"
cat > "$E2/meta.json" <<'JSON'
{"titulo": "Planilha de custos", "tipo": "planilha"}
JSON
cat > "$E2/planilha.json" <<'JSON'
{"abas": [{"nome": "Custos", "colunas": ["Item", "Qtd", "Preço", "Total"],
  "formatos": ["texto", "numero", "moeda", "moeda"],
  "linhas": [["Arroz", 2, 6.5, "=B2*C2"], ["Frango", 3, 18.9, "=B3*C3"], ["Total", "", "", "=SUM(D2:D3)"]],
  "larguras": [20, 8, 12, 12]}]}
JSON
espera_saida 0 "$PY" "$S3/entregavel_planilha.py" --pasta "$E2"
passo "03: remontar a página pro carrossel aparecer"
espera_saida 0 "$PY" "$S2/pagina_render.py" --projeto "$P"
# o render renomeia as fotos do carrossel pra img/carrossel-NN (na ordem dos nomes: 01-guia… primeiro)
if grep -q 'img/carrossel-01.jpg' "$P/pagina/site/index.html" 2>/dev/null \
   && cmp -s "$P/pagina/imagens/carrossel/01-guia-marmitas-01.jpg" "$P/pagina/site/img/carrossel-01.jpg"; then
  ok "carrossel com a capa do guia na página"
else
  falha "carrossel do guia não apareceu na página remontada"
fi

# ─────────────────────────────── 04 Anúncios ───────────────────────────────
passo "04: anuncios.json (1 estático com o guia + 1 vídeo), riscos, criativos e exportar"
mkdir -p "$P/anuncios"
cat > "$P/anuncios/anuncios.json" <<'JSON'
{"anuncios": [
  {"id": "dor-cozinha", "angulo": "Cansaço de cozinhar todo dia", "formato": "estatico",
   "headline_imagem": "Comida pronta pra **15 dias**",
   "texto_principal": "Chega em casa sem energia pra cozinhar?\nCom o Domingo Único você prepara tudo num domingo.",
   "titulo": "Marmitas pra 15 dias", "descricao": "Receitas testadas", "cta": "Saiba mais",
   "visual": {"prompt": "marmitas coloridas em potes de vidro, luz natural", "produto": "guia-marmitas", "layout": "base"}},
  {"id": "video-rotina", "angulo": "Rotina corrida", "formato": "video",
   "hooks": ["Se você chega em casa sem energia pra cozinhar, olha isso.", "Eu cozinho uma vez e como bem por 15 dias."],
   "corpo": "Eu vivia pedindo delivery. Aí organizei um domingo só pra cozinhar.",
   "cta_falado": "Toca em saiba mais e veja as receitas.",
   "cenas": ["Geladeira cheia de marmitas", "Montando os potes"],
   "texto_principal": "Uma tarde de domingo, 15 dias de comida pronta.", "titulo": "Marmitas pra 15 dias", "cta": "Saiba mais"}
]}
JSON
espera_saida 0 "$PY" "$S4/anuncio_riscos.py" --pasta "$P/anuncios"
espera_saida 0 "$PY" "$S4/anuncio_criativo.py" --projeto "$P"
if grep -qi 'não achei o mockup' "$SAIDA"; then falha "anuncio_criativo não achou o mockup do guia"; fi
espera_saida 0 "$PY" "$S4/anuncio_exportar.py" --projeto "$P"

# ─────────────────────────────── 05 Funil ───────────────────────────────
passo "05: funil.json, mapa, downsell (texto) e upsell (vídeo)"
mkdir -p "$P/funil/downsell" "$P/funil/upsell"
cat > "$P/funil/funil.json" <<'JSON'
{"front":    {"nome": "Marmitas Já", "preco": 27},
 "bump":     {"nome": "Lista de compras inteligente", "preco": 9.9, "conversao": 0.2},
 "upsell":   {"nome": "Cardápio 30 dias", "preco": 72, "conversao": 0.10},
 "downsell": {"nome": "Cardápio 15 dias", "preco": 37, "conversao": 0.10}}
JSON
espera_saida 0 "$PY" "$S5/funil_mapa.py" --projeto "$P"
cat > "$P/funil/downsell/oto.json" <<'JSON'
{"formato": "texto",
 "texto": "Espera: o Cardápio 30 dias não era pra agora?\n\nEntão leve a versão de 15 dias, pela metade do preço.",
 "checkout_url": "https://pay.kiwify.com.br/downsell123",
 "recusar_url": "https://obrigado.exemplo.com.br/marmitas"}
JSON
espera_saida 0 "$PY" "$S5/funil_oto.py" --pasta "$P/funil/downsell" --paleta 'verde-branco'
espera_saida 3 "$PY" "$S5/funil_oto.py" --pasta "$P/funil/downsell" --paleta 'verde-branco' --publicar
espera_saida 0 "$PY" "$S5/funil_oto.py" --pasta "$P/funil/downsell" --definir-url 'https://downsell-teste.netlify.app'
cat > "$P/funil/upsell/oto.json" <<'JSON'
{"formato": "video", "video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
 "checkout_url": "https://pay.kiwify.com.br/upsell123", "atraso_segundos": 45,
 "recusar_url": "https://downsell-teste.netlify.app"}
JSON
espera_saida 0 "$PY" "$S5/funil_oto.py" --pasta "$P/funil/upsell" --paleta 'verde-branco'
espera_saida 3 "$PY" "$S5/funil_oto.py" --pasta "$P/funil/upsell" --paleta 'verde-branco' --publicar
grep -q 'downsell-teste.netlify.app' "$P/funil/upsell/site/index.html" 2>/dev/null \
  && ok "upsell recusa vai pro downsell" || falha "recusar_url do upsell não apareceu na página"

# ─────────────────────────────── Conferência final ───────────────────────────────
passo "Conferindo os arquivos gerados"
ESPERADOS=(
  "$B/ofertas.json" "$B/ofertas.md" "$P/pesquisa/escolhida.json"
  "$P/pagina/config.json" "$P/pagina/site/index.html"
  "$E/capa.png" "$E/mockup.png" "$E/guia-marmitas.pdf" "$E/previa/amostra-1.png" "$E/previa/amostra-2.png"
  "$P/pagina/imagens/carrossel/01-guia-marmitas-01.jpg"
  "$E2/planilha-custos.xlsx"
  "$P/anuncios/criativos/dor-cozinha-1x1.jpg" "$P/anuncios/criativos/dor-cozinha-9x16.jpg"
  "$P/anuncios/textos.md" "$P/anuncios/roteiros.md" "$P/anuncios/plano-de-teste.xlsx"
  "$P/funil/mapa.png"
  "$P/funil/downsell/site/index.html" "$P/funil/upsell/site/index.html"
)
for arq in "${ESPERADOS[@]}"; do
  if [ -s "$arq" ]; then ok "${arq#"$P"/}"; else falha "faltou ${arq#"$P"/}"; fi
done
aluno "$PY" - "$E/guia-marmitas.pdf" "$E2/planilha-custos.xlsx" "$P/anuncios/plano-de-teste.xlsx" \
  "$E/capa.png" "$P/anuncios/criativos/dor-cozinha-9x16.jpg" "$P/funil/mapa.png" <<'PY' \
  && ok "PDF, xlsx e imagens são arquivos válidos" || falha "algum arquivo gerado está corrompido"
import struct, sys, zipfile
pdf, x1, x2, capa, jpg, mapa = sys.argv[1:]
assert open(pdf, "rb").read(5) == b"%PDF-", pdf
for x in (x1, x2):
    assert zipfile.is_zipfile(x) and "xl/workbook.xml" in zipfile.ZipFile(x).namelist(), x
def png_tamanho(p):
    h = open(p, "rb").read(24)
    assert h[:8] == b"\x89PNG\r\n\x1a\n", p
    return struct.unpack(">II", h[16:24])
assert png_tamanho(capa) == (1240, 1754), png_tamanho(capa)
png_tamanho(mapa)
assert open(jpg, "rb").read(3) == b"\xff\xd8\xff", jpg
PY
[ ! -e "$P/anuncios/plano-de-teste.csv" ] && ok "plano saiu em .xlsx (03 instalado)" || falha "plano saiu em .csv"

passo "Conferindo que o ~ real não foi tocado"
[ "$(carimbo_real)" = "$CARIMBO_ANTES" ] && ok "~/.maquina, ~/.claude/skills e ~/MaquinaIA intactos" \
  || falha "algo mudou no HOME real durante o teste"

echo
if [ ${#FALHAS[@]} -eq 0 ]; then
  echo "✅ Pacote aprovado ($(basename "$ZIP"))"
  exit 0
fi
echo "❌ Pacote reprovado — ${#FALHAS[@]} problema(s):"
for f in "${FALHAS[@]}"; do echo "   - $f"; done
exit 1
