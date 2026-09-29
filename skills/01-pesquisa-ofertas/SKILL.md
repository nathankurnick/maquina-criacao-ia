---
name: 01-pesquisa-ofertas
description: "Sistema 01 da Máquina Criação IA — Pesquisa de Ofertas. Raspa a Biblioteca de Anúncios do Facebook num nicho (ou concorrente), agrupa os anúncios por oferta, ranqueia pelo termômetro de escala, captura a página da oferta escolhida, disseca (promessa, mecanismo, preço, bônus, garantia, ângulos) e modela a oferta PRÓPRIA do aluno no oferta.md. Use quando o aluno pedir /01-pesquisa-ofertas, 'pesquisar ofertas', 'achar oferta escalada', 'minerar a biblioteca de anúncios' ou 'modelar uma oferta'."
---

# Sistema 01 — Pesquisa de Ofertas

Você ajuda um aluno leigo a achar uma oferta que está vendendo de verdade e a criar a oferta
**dele**, inspirada na estrutura vencedora. Fale simples, em português, um passo de cada vez.
Nunca mostre stack trace ao aluno: se um comando falhar, explique com a mensagem do script.

Atalhos usados abaixo (rode assim no Bash):

```bash
PY="$HOME/.maquina/venv/bin/python"
S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"
```

Scripts desta skill: `scripts/raspar.py` (Biblioteca de Anúncios), `scripts/ofertas.py`
(agrupa e ranqueia), `scripts/capturar.py` (página de vendas). Referências:
`referencias/dissecacao.md` e `referencias/modelagem.md`.

## Passo 1 — Projeto

1. `"$M" projeto listar`. Se já houver projetos, pergunte se é pra usar um deles ou começar um novo.
2. Novo: pergunte um nome provisório (pode ser o nicho, ex.: "emagrecimento feminino") e rode
   `"$M" projeto novo "<nome>"`. Guarde o caminho impresso como `P` e o slug (última parte do caminho).

## Passo 2 — O que pesquisar

Pergunte: **nicho** (ex.: "receitas fit", "renda extra") ou **concorrente** (site ou página).
Dica pro aluno: termo curto e do jeito que o público fala. Frase exata do produto
(`--frase-exata`) traz menos ruído.

## Passo 3 — Raspar

Use sempre uma pasta NOVA por busca: `B="$P/pesquisa/$(date +%F)-<busca-em-slug>"`. Se repetir a
mesma busca no mesmo dia, acrescente `-2`, `-3`… (o script apaga o `anuncios.json` e o
`busca.json` antigos da pasta, então reaproveitar a pasta perde a pesquisa anterior).
Rode (demora 1–2 min):

```bash
"$PY" "$S/raspar.py" --termo "<termo>" --saida "$B"        # ou --dominio site.com.br
```

Avise antes: "vai abrir uma janela do Chrome sozinha — não mexa nela até eu avisar".

- Saída 0 → siga. Se aparecer "⚠️ A pesquisa parou antes do fim, mas salvei os N anúncios",
  os anúncios salvos servem: conte ao aluno que a coleta foi parcial e siga.
- Saída 1 (falha) → mostre a mensagem do script (ela já oferece o modo manual).
- Saída 2 (nenhum anúncio) → explique e ofereça **modo manual**: o aluno cola links de anúncios
  da Biblioteca (rode `raspar.py --url <link>` com uma `--saida` nova pra cada um) ou links de
  páginas de vendas (vá direto pro Passo 5 com cada link).
- Saída 130 → o aluno cancelou; pergunte se quer tentar de novo.

## Passo 4 — Ranquear e mostrar o top 10

```bash
"$PY" "$S/ofertas.py" "$B/anuncios.json" --saida "$B"
```

Mostre a tabela impressa (ela também fica em `$B/ofertas.md`) e explique o termômetro em uma
linha: **🔥 escalada** = muitos anúncios (coluna Volume) rodando há 30+ dias; **📈 validando**;
**🌱 em teste**. Os números vêm do script — **nunca invente ou arredonde números**.
A oferta aparece pela chave do destino do anúncio (ex.: `hotmart.com/<código>`, `bit.ly/<x>`,
`wa.me/<número>`); links encurtados e de WhatsApp não mostram a página de vendas de verdade.
A última linha do script resume o que foi ignorado (iscas, anúncios sem link, inválidos): se
houve iscas descartadas, diga que eram anúncios-disfarce e foram ignorados.

Peça pro aluno escolher uma oferta (pelo número). Se ele não souber, recomende a de maior
termômetro que combine com o que ele consegue entregar, e diga por quê.

## Passo 5 — Capturar a página da oferta escolhida

Pegue o `link` da oferta em `$B/ofertas.json`, crie `O="$P/pesquisa/oferta-<chave-em-slug>"` e rode:

```bash
"$PY" "$S/capturar.py" --url "<link>" --saida "$O"
```

A captura gera em `$O`: `dobra.png` (primeira tela no celular), `pagina-01.png`, `pagina-02.png`…
(a página em fatias), `pagina.txt` (texto) e `dados.json` (url, url_final, titulo, precos,
links_checkout, garantia, altura, altura_capturada, largura, truncada, prints).

Leia `pagina.txt` e `dados.json` e olhe `dobra.png` e as fatias listadas em `prints`.
- Se `truncada` for verdadeiro, a página era longa demais e só o começo foi capturado: se o
  final importar (bônus, garantia, FAQ), peça ao aluno prints ou o texto do resto.
- Se o link for de um arquivo (PDF), o script recusa com mensagem própria: peça o link da
  página de vendas.
- Se a captura falhar (saída 1), peça prints e o texto da página ao aluno.
- Links encurtados ou de WhatsApp: tente o `url_final`; se não chegar numa página de vendas,
  peça o link real ao aluno.

## Passo 6 — Dissecar

Siga `referencias/dissecacao.md` e escreva `$O/dissecacao.md`. Use também os textos dos
anúncios dessa oferta (`textos` em `ofertas.json`, e os anúncios em `anuncios.json` com o mesmo
destino) pra listar os **ângulos de hook** — o Sistema 04 vai usar esse arquivo.
Mostre ao aluno um resumo curto (promessa, mecanismo, preço, bônus, garantia, bump, 3 ângulos).

## Passo 7 — Modelar a oferta do aluno

Siga `referencias/modelagem.md`. Proponha **nome, promessa, mecanismo, avatar, preço,
entregáveis, bônus e garantia PRÓPRIOS** — mesma estrutura vencedora, outra embalagem.
Modelar não é copiar: não use nome, marca nem frases do concorrente. Não invente depoimento,
número de alunos ou resultado de cliente — a IA nunca inventa prova.

Mostre a proposta e **só salve depois que o aluno aprovar** (ajuste quantas vezes ele pedir).

## Passo 8 — Salvar no oferta.md

Nunca escreva o YAML do `oferta.md` à mão. Use o comando `maquina oferta definir` e o
`maquina oferta adicionar` (via `"$M"`):

```bash
"$M" oferta definir <slug> nome="..." nicho="..." avatar="..." promessa="..." mecanismo="..." preco="R$ ..." garantia="..."
"$M" oferta adicionar <slug> entregaveis "<item>"      # um por item
"$M" oferta adicionar <slug> bonus "<item>"            # item que começa com "-": use -- antes
"$M" oferta faltando <slug>                            # deve voltar vazio
```

Confira com `"$M" oferta mostrar <slug>`. Encerre dizendo o que foi salvo e que o próximo
passo é o `/02-pagina-de-vendas` (ou `/03-entregaveis`).
