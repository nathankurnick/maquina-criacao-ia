---
name: 01-pesquisa-ofertas
description: "Sistema 01 da Máquina Criação IA — Pesquisa de Ofertas. Raspa a Biblioteca de Anúncios do Facebook num nicho (ou concorrente), agrupa os anúncios por oferta, ranqueia pelo termômetro de escala, captura a página da oferta escolhida, disseca (promessa, mecanismo, preço, bônus, garantia, ângulos) e modela a oferta PRÓPRIA do aluno no oferta.md. Use quando o aluno pedir /01-pesquisa-ofertas, 'pesquisar ofertas', 'achar oferta escalada', 'minerar a biblioteca de anúncios' ou 'modelar uma oferta'."
---

# Sistema 01 — Pesquisa de Ofertas

Você ajuda um aluno leigo a achar uma oferta que está vendendo de verdade e a criar a oferta
**dele**, inspirada na estrutura vencedora. Fale simples, em português, um passo de cada vez.
Nunca mostre stack trace ao aluno: se um comando falhar, explique com a mensagem do script.

**Regra dos comandos (importante):** variáveis de shell NÃO persistem entre chamadas do Bash.
Todo comando Bash desta skill começa com este prefixo de uma linha, colado por inteiro **em
TODA chamada** (`PFX` abaixo significa "cole esta linha antes do comando"):

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; M="$(command -v maquina || echo "$HOME/.local/bin/maquina")";
```

As pastas do projeto, da busca e da oferta (`P`, `B`, `O` nos exemplos) são **caminhos absolutos
literais** que você anotou da saída de comandos anteriores — escreva o caminho de verdade no
comando, nunca uma variável de shell.

**Aspas:** valores de `maquina oferta definir` / `adicionar` sempre em aspas simples
(`preco='R$ 97,00'`), porque `$` em aspas duplas some. Apóstrofo dentro do valor vira `'\''`.

Scripts desta skill: `scripts/raspar.py` (Biblioteca de Anúncios), `scripts/ofertas.py`
(agrupa e ranqueia), `scripts/capturar.py` (página de vendas). Referências:
`referencias/dissecacao.md` e `referencias/modelagem.md`.

## Passo 1 — Projeto

1. `PFX "$M" projeto listar`. Se já houver projetos, pergunte se é pra usar um deles ou começar um novo.
2. Novo: pergunte um nome provisório (pode ser o nicho, ex.: "emagrecimento feminino") e rode
   `PFX "$M" projeto novo "<nome>"`. Anote o caminho impresso (`P`) e o slug (última parte do caminho).
3. Existente: rode `PFX "$M" projeto caminho <slug>` e anote o caminho.
   Antes de modelar num projeto que já tem oferta, rode `PFX "$M" oferta mostrar <slug>` e avise:
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
PFX "$PY" "$S/raspar.py" --termo "<termo>" --saida "<B>"        # ou --dominio site.com.br
```

- Saída 0 → siga. Se aparecer "⚠️ A pesquisa parou antes do fim, mas salvei os N anúncios",
  os anúncios salvos servem: conte ao aluno que a coleta foi parcial e siga.
- Saída 1 (falha) → mostre a mensagem do script (ela já oferece o modo manual).
- Saída 2 (nenhum anúncio) → explique e ofereça o **modo manual** (abaixo).
- Saída 130 → o aluno cancelou. Se houver salvamento parcial e existir `anuncios.json` na pasta,
  ofereça continuar com o que foi salvo; senão pergunte se quer tentar de novo (em pasta nova).

**Modo manual** (o aluno cola links):
- Link da Biblioteca de Anúncios: rode `raspar.py --url "<link>" --saida "<pasta nova>"` para cada
  link, cada um numa pasta nova, e depois rode o Passo 4 (`ofertas.py`) em cada uma. Avise que o
  termômetro com poucos anúncios é fraco — apresente como **indicativo**.
- Link de página de vendas: pule direto pro Passo 5 com cada link.

## Passo 4 — Ranquear e mostrar o top 10

```bash
PFX "$PY" "$S/ofertas.py" "<B>/anuncios.json" --saida "<B>"
```

Se sair com código 1, mostre a mensagem do script ao aluno e pergunte como quer seguir.
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

## Passo 5 — Capturar a página da oferta escolhida

Pegue o `link` de `ofertas[N-1]` em `<B>/ofertas.json` e crie a pasta da oferta
`<P>/pesquisa/oferta-<chave-em-slug>` (ex.: chave `hotmart.com/abc` → `oferta-hotmart-com-abc`), `O`. Rode:

```bash
PFX "$PY" "$S/capturar.py" --url "<link>" --saida "<O>"
```

Se sair com 130 ou 1, mostre a mensagem do script e pergunte ao aluno como seguir.
A captura gera em `<O>`: `dobra.png` (primeira tela no celular), `pagina-01.png`, `pagina-02.png`…
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

Siga `referencias/dissecacao.md` e escreva `<O>/dissecacao.md`. Use também os textos dos
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
`maquina oferta adicionar` (via `"$M"`, com o prefixo). Valores sempre em aspas simples;
apóstrofo dentro do valor vira `'\''`:

```bash
PFX "$M" oferta definir <slug> nome='...' nicho='...' avatar='...' promessa='...' mecanismo='...' preco='R$ 97,00' garantia='...'
PFX "$M" oferta adicionar <slug> entregaveis '<item>'      # um por item
PFX "$M" oferta adicionar <slug> bonus '<item>'            # item que começa com "-": use -- antes
PFX "$M" oferta faltando <slug>                            # deve voltar vazio
```

Confira com `PFX "$M" oferta mostrar <slug>`. Encerre dizendo o que foi salvo e que o próximo
passo é o `/02-pagina-de-vendas` (ou `/03-entregaveis`).
