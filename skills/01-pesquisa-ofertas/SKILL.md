---
name: 01-pesquisa-ofertas
description: "Sistema 01 da Máquina Criação IA — Pesquisa de Ofertas. Raspa a Biblioteca de Anúncios do Facebook num nicho (ou concorrente), agrupa os anúncios por oferta, ranqueia pelo termômetro de escala, captura a página da oferta escolhida, disseca (promessa, mecanismo, preço, bônus, garantia, ângulos) e modela a oferta PRÓPRIA do aluno no oferta.md. Use quando o aluno pedir /01-pesquisa-ofertas, 'pesquisar ofertas', 'achar oferta escalada', 'minerar a biblioteca de anúncios' ou 'modelar uma oferta'."
---

# Sistema 01 — Pesquisa de Ofertas

Você ajuda um aluno leigo a achar uma oferta que está vendendo de verdade e a criar a oferta
**dele**, inspirada na estrutura vencedora. Fale simples, em português, um passo de cada vez.
Nunca mostre stack trace ao aluno: se um comando falhar, explique com a mensagem do script.

**Regra dos comandos (importante):** variáveis de shell NÃO persistem entre chamadas do Bash —
cada comando Bash é independente: sempre inclua as definições no início da linha, exatamente
como nos exemplos (só as variáveis que o comando usa: `PY`, `S`, `M`).

As pastas do projeto, da busca e da oferta (`P`, `B`, `O` nos exemplos) são **caminhos absolutos
literais** que você anotou da saída de comandos anteriores — escreva o caminho de verdade no
comando, nunca uma variável de shell.

**Aspas:** valores de `maquina oferta definir` / `adicionar` sempre em aspas simples
(`preco='R$ 97,00'`), porque `$` em aspas duplas some. Apóstrofo dentro do valor vira `'\''`.

Scripts desta skill: `scripts/raspar.py` (Biblioteca de Anúncios), `scripts/ofertas.py`
(agrupa e ranqueia), `scripts/capturar.py` (página de vendas), `scripts/baixar_criativos.py`
(baixa imagem e vídeo dos anúncios da oferta escolhida) e `scripts/registrar_escolha.py`
(anota a escolha). Referências:
`referencias/dissecacao.md` e `referencias/modelagem.md`.

## Passo 1 — Projeto

1. `M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto listar`. Se já houver projetos, pergunte se é pra usar um deles ou começar um novo.
2. Novo: pergunte um nome provisório (pode ser o nicho, ex.: "emagrecimento feminino") e rode
   `M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto novo "<nome>"`. Anote o caminho impresso (`P`) e o slug (última parte do caminho).
3. Existente: rode `M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto caminho <slug>` e anote o caminho.
   Antes de modelar num projeto que já tem oferta, rode `M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta mostrar <slug>` e avise:
   "`adicionar` acrescenta às listas que já existem (não há comando de remover)". Pergunte se
   ele quer manter esse projeto ou começar um novo.

## Passo 2 — O que pesquisar

Pergunte: **nicho** (ex.: "receitas fit", "renda extra") ou **concorrente**.
- Nicho: termo curto, do jeito que o público fala. Frase exata do produto (`--frase-exata`) traz menos ruído.
- Concorrente com site: use `--dominio site.com.br`.
- Concorrente que é página do Facebook: use `--termo "<nome da página>" --frase-exata`.

## Passo 3 — Raspar

Use sempre uma pasta NOVA por busca: `<P>/pesquisa/<data AAAA-MM-DD>-<busca-em-slug>` (escreva o
caminho literal). Repetir uma busca exige pasta nova (`-2`, `-3`…), porque o script apaga o
`anuncios.json` e o `busca.json` antigos da pasta — reaproveitar a pasta perde a pesquisa anterior.
Avise antes: "vai abrir uma janela do Chrome sozinha — não mexa nela até eu avisar". Rode (1–2 min):

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S/raspar.py" --termo "<termo>" --saida "<B>"        # ou --dominio site.com.br
```

- Saída 0 → siga. Se aparecer "⚠️ A pesquisa parou antes do fim, mas salvei os N anúncios",
  os anúncios salvos servem: conte ao aluno que a coleta foi parcial e siga.
- Saída 1 (falha) → mostre a mensagem do script (ela já oferece o modo manual).
- Saída 2 (nenhum anúncio) → explique e ofereça o **modo manual** (abaixo).
- Saída 130 → o aluno cancelou. Se houver salvamento parcial e existir `anuncios.json` na pasta,
  ofereça continuar com o que foi salvo; senão pergunte se quer tentar de novo (em pasta nova).

**Modo manual** (o aluno cola links):
- Link da Biblioteca de Anúncios: rode, um por link, em pastas novas `-link-1`, `-link-2`… (uma
  por link):

  ```bash
  PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S/raspar.py" --url "<link>" --saida "<P>/pesquisa/AAAA-MM-DD-link-1"
  ```

  Depois rode o Passo 4 (`ofertas.py`) em cada pasta. Avise que o termômetro com poucos anúncios
  é fraco — apresente como **indicativo**. Com vários links você terá várias tabelas, cada uma
  numerada a partir de 1: mostre-as separadas e pergunte "link X, oferta N".
- Link de página de vendas: pule direto pro Passo 5 com cada link; a pasta da oferta é
  `<P>/pesquisa/oferta-<domínio-em-slug>` (ex.: `site.com.br` → `oferta-site-com-br`).

## Passo 4 — Ranquear e mostrar o top 10

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S/ofertas.py" "<B>/anuncios.json" --saida "<B>"
```

Se sair com código 1, mostre a mensagem do script ao aluno e pergunte como quer seguir.
Se sair com **código 2**, nenhuma oferta tem página de vendas (só anúncios sem link ou de
mensagem): mostre a mensagem do script e ofereça outro termo, o `--dominio` de um concorrente
ou o modo manual. Não invente oferta.
Mostre a tabela impressa (ela também fica em `<B>/ofertas.md`) e explique o termômetro em uma
linha: **🔥 escalada** = muitos anúncios (coluna Volume) rodando há 30+ dias; **📈 validando**;
**🌱 em teste**. Os números vêm do script — **nunca invente ou arredonde números**.
A oferta aparece pela chave do destino do anúncio (ex.: `hotmart.com/<código>`, `bit.ly/<x>`,
`wa.me/<número>`, `whatsapp:<página>` quando o link de WhatsApp não tem telefone); links
encurtados e de WhatsApp não mostram a página de vendas de verdade.
A última linha do script resume o que foi ignorado (iscas, anúncios sem link, inválidos): se
houve iscas descartadas, diga que eram anúncios-disfarce e foram ignorados.

Peça pro aluno escolher uma oferta (pelo número). O número N da tabela é `ofertas[N-1]` em
`<B>/ofertas.json` (mesma ordem da tabela). Se ele não souber, recomende a de maior termômetro
que combine com o que ele consegue entregar, e diga por quê.

## Passo 5 — Registrar a escolha, baixar os criativos e capturar a página

Pegue o `link` de `ofertas[N-1]` em `<B>/ofertas.json` e crie a pasta da oferta `O` =
`<P>/pesquisa/oferta-<chave-em-slug>`. **Regra do slug:** tudo minúsculo, sem acentos, e cada
sequência de caracteres que não seja letra ou número vira um único `-` (sem `-` nas pontas).
Exemplos: `hotmart.com/abc` → `oferta-hotmart-com-abc`; `whatsapp:Página Ágil` →
`oferta-whatsapp-pagina-agil`.

**Faça isto logo depois que o aluno escolher** — os links de vídeo e imagem do Facebook expiram
em poucas horas. Primeiro registre a escolha:

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S/registrar_escolha.py" --busca "<B>" --oferta N --pasta-oferta "<O>"
```

(grava `<P>/pesquisa/escolhida.json` com busca, oferta, chave, pasta_oferta e data; o Sistema 04 lê
esse arquivo). Depois baixe os criativos (as 10 primeiras cópias da oferta; para o Sistema 04):

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S/baixar_criativos.py" --anuncios "<B>/anuncios.json" --ofertas "<B>/ofertas.json" --oferta N --saida "<O>/anuncios"
```

Isso cria `<O>/anuncios/` com os arquivos e o `criativos.json` (id, pagina, texto, cta, link,
arquivos e o link da Biblioteca de cada anúncio). Se sair 1, mostre a mensagem e siga assim
mesmo; se avisar que nenhum arquivo baixou, siga só com os textos. Em seguida capture a página:

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S/capturar.py" --url "<link>" --saida "<O>"
```

Se sair com 130 ou 1, mostre a mensagem do script e pergunte ao aluno como seguir.
A captura gera em `<O>`: `dobra.png` (primeira tela no celular), `pagina-01.png`, `pagina-02.png`…
(a página em fatias), `pagina.txt` (texto) e `dados.json` (url, url_final, titulo, precos,
links_checkout, garantia, altura, altura_capturada, largura, truncada, prints).

**Checkout / order bump:** se `links_checkout` em `dados.json` não estiver vazio, capture também
o primeiro link de checkout, em `<O>/checkout`:

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S/capturar.py" --url "<primeiro link_checkout>" --saida "<O>/checkout"
```

Se falhar, siga sem ele (é só um extra). No Passo 6 use o `pagina.txt`, os `precos` e as fatias
desse checkout para achar **order bump** e **preço real**; o que não aparecer, "não encontrado".

Leia `pagina.txt` e `dados.json` e olhe `dobra.png` e as fatias listadas em `prints`.
- Se `truncada` for verdadeiro, a página era longa demais e só o começo foi capturado: se o
  final importar (bônus, garantia, FAQ), peça ao aluno prints ou o texto do resto.
- Se o link for de um arquivo (PDF), o script recusa com mensagem própria: peça o link da
  página de vendas.
- Se a captura falhar (saída 1), peça prints e o texto da página ao aluno.
- Links encurtados ou de WhatsApp: tente o `url_final`; se não chegar numa página de vendas,
  peça o link real ao aluno.

## Passo 6 — Dissecar

Siga `referencias/dissecacao.md` e escreva `<O>/dissecacao.md` (com as linhas `Busca:` e `Chave:`
da ficha). Use também os `textos` da oferta em `ofertas.json` (já são as cópias mais repetidas) e
o `<O>/anuncios/criativos.json` pra listar os **ângulos de hook**: cada ângulo leva o **id de um
anúncio de exemplo** (dos `ids` da oferta) e a **primeira linha literal** do texto desse anúncio.
Isso é só **REFERÊNCIA** para o Sistema 04 — não vai para a copy do aluno e ninguém deve copiar
essas frases. O Sistema 04 vai usar esse arquivo. Sem `ofertas.json` (veio de link de página de vendas), tire os ângulos da
própria página ou de textos de anúncio que o aluno colar.
Mostre ao aluno um resumo curto (promessa, mecanismo, preço, bônus, garantia, bump, 3 ângulos).

## Passo 7 — Modelar a oferta do aluno

Siga `referencias/modelagem.md`. Proponha **nome, promessa, mecanismo, avatar, preço,
entregáveis, bônus e garantia PRÓPRIOS** — mesma estrutura vencedora, outra embalagem.
Modelar não é copiar: não use nome, marca nem frases do concorrente. Não invente depoimento,
número de alunos ou resultado de cliente — a IA nunca inventa prova.

Mostre a proposta e **só salve depois que o aluno aprovar** (ajuste quantas vezes ele pedir).

## Passo 8 — Salvar no oferta.md

Nunca escreva o YAML do `oferta.md` à mão. Use o comando `maquina oferta definir` e o
`maquina oferta adicionar` (via `"$M"`, com a definição de `M` no início). Valores sempre em aspas simples;
apóstrofo dentro do valor vira `'\''`:

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta definir <slug> nome='...' nicho='...' avatar='...' promessa='...' mecanismo='...' preco='R$ 97,00' garantia='...'
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta adicionar <slug> entregaveis '<item>'      # um por item
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta adicionar <slug> bonus '<item>'
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta adicionar <slug> bonus -- '-50% no combo'   # item que começa com "-": use --
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta faltando <slug>                            # deve voltar vazio
```

Confira com `M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta mostrar <slug>`. Encerre dizendo o que foi salvo e que o próximo
passo é o `/02-pagina-de-vendas` (ou `/03-entregaveis`).
