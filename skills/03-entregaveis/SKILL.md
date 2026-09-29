---
name: 03-entregaveis
description: "Sistema 03 da Máquina Criação IA — Criar Entregáveis. Monta o mapa de entregáveis a partir do produto e dos bônus do oferta.md, escreve o conteúdo completo (ebook, guia, checklist, roteiro de aulas, slides, planilha), gera o PDF diagramado na paleta da página, a capa, o mockup 3D e as imagens pro carrossel da página de vendas. Use quando o aluno pedir /03-entregaveis, 'criar o ebook', 'fazer os bônus', 'montar o material do curso', 'gerar o PDF', 'capa do ebook' ou 'mockup'."
---

# Sistema 03 — Criar Entregáveis

Você produz o material que o aluno vai entregar a quem comprar. Fale simples, um passo por
vez, sem termos técnicos. Ele aprova o mapa e cada peça grande antes de você seguir.

**Cada comando Bash é independente**: cole as definições no começo de cada comando, exatamente
como nos exemplos, e troque `<P>` (pasta do projeto) e `<E>` (pasta do entregável) por caminhos
absolutos, entre aspas. Valores do `maquina oferta` sempre em aspas simples (apóstrofo vira `'\''`).

Scripts: `scripts/entregavel_pdf.py` (PDF + amostras), `scripts/entregavel_capa.py` (capa e
mockup), `scripts/entregavel_planilha.py` (.xlsx). Referências: `referencias/formatos.md`
(qual formato usar), `referencias/escrita.md` (como escrever e o Markdown aceito).

Todos os scripts terminam com código 0 (ok), 1 (problema previsto: leia a mensagem em
português, mostre ao aluno e corrija) ou 130 (cancelado). Nunca mostre erro técnico ao aluno.

## Passo 1 — Projeto e oferta

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto listar
```

Se houver mais de um, pergunte qual. Depois:

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto caminho <slug>; "$M" oferta mostrar <slug>
```

O `maquina oferta mostrar` imprime JSON com os dados da oferta (só se altera via
`maquina oferta definir|adicionar`). Anote o caminho como `<P>`, as listas `entregaveis` e `bonus`
e a paleta, nesta ordem: se existir `<P>/pagina/config.json`, leia-o e use a `paleta` dele (é a
que está na página de vendas); senão a `paleta` da oferta; se ambas estiverem vazias, use
`azul-laranja` e diga ao aluno que dá pra escolher outra no Sistema 02. Se existir
`<P>/pesquisa/dissecacao.md`, leia: ajuda a acertar o que o público espera do material.

## Passo 2 — Mapa de entregáveis

Pra cada item de `entregaveis` e `bonus`, proponha um formato (`referencias/formatos.md`) e um
tamanho. Mostre o mapa como tabela e peça pro aluno aprovar ou trocar. Só siga depois do "pode".
Se ele quiser um item que não está no oferta.md, grave antes com `maquina oferta adicionar`:

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta adicionar <slug> bonus 'Checklist de compras'
```

Se o texto do item começa com "-", coloque `--` antes dele para não ser lido como opção.

## Passo 3 — Escrever cada entregável

Pra cada item aprovado, crie a pasta `<P>/entregaveis/<slug-do-item>/` (ex.: `ebook-pao-caseiro`;
o nome da pasta vira o nome do arquivo final e das imagens do carrossel: só minúsculas, sem acento,
com hífens, sem espaços) com:

- `meta.json`: `{"titulo": "...", "subtitulo": "...", "tipo": "ebook", "autor": "<nome do aluno>"}`
  (`tipo`: ebook, guia, checklist, roteiro, slides ou planilha; só `titulo` é obrigatório).
- `conteudo.md`: o texto completo, seguindo `referencias/escrita.md`.
- Planilha: em vez de `conteudo.md`, um `planilha.json` com
  `{"abas": [{"nome": "...", "colunas": [...], "linhas": [[...]], "larguras": [...]}]}`
  (`larguras` é opcional; texto começando com `=` vira fórmula). Fórmulas sempre em **inglês e
  com vírgula**: `=SUM(C2:C31)`, `=IF(A2>0,1,0)` (as mais comuns em português, como `SOMA` e `SE`, e o `;` são
  recusadas; escreva sempre em inglês). Números vão como números do JSON (`420`, não `"420"`). Opcional por aba:
  `"formatos": ["texto", "numero", "moeda", "percentual", "data"]`, um por coluna na ordem de
  `colunas` (moeda sai como R$; data aceita `"2026-10-01"`).
- Imagens dentro do conteúdo: arquivos em `imagens/` com nome em minúsculas, sem acento, com
  hífens, de até ~1600 px de largura.
- Roteiro e slides são material **interno** do curso: roteiro não tem capa,
  não vai pro carrossel e só sobe na área de membros se o aluno quiser vendê-lo como apostila;
  slides: um deck por aula, sem carrossel por padrão.

Material grande: escreva capítulo por capítulo, mostrando cada um ao aluno; ele aprova antes de
você gerar. Nunca invente prova nem estudo. Faltou prova (depoimento, número de alunos, resultado de
cliente): escreva "[cole aqui um depoimento real]" (ou o item que faltar) e pergunte ao aluno.
Faltou estudo, estatística ou citação: marque "(confirme esta informação)" e pergunte.

## Passo 4 — Capa e mockup (ebook, guia, checklist)

Faça a capa **antes** do PDF: se `capa.png` existir, o PDF a usa como primeira página.

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/03-entregaveis/scripts"; "$PY" "$S/entregavel_capa.py" --pasta "<E>" --paleta '<paleta>' --arte '<descrição visual, sem texto>'
```

- `--arte` é opcional: descreva só o visual (cena, luz, cores, estilo; nada de texto escrito na
  imagem). **Com a chave KIE ele espera até ~150 s e baixa a imagem: rode este comando com
  timeout do Bash de 5 minutos (300000 ms).** Sem `--arte`, o comando é rápido.
- Sem a chave KIE, o script mostra o prompt e pede pra salvar a arte como `arte.png` dentro de
  `<E>`; a capa sai com fundo na cor da paleta. Se o aluno gerar a arte em outra ferramenta e
  salvar `arte.png`, rode o comando de novo (sem `--arte`, o `arte.png` é usado).
- Se já existir um `arte.png` antigo, o script o reutiliza e avisa. Se a arte não for a desejada,
  apague o `arte.png` e refaça.
- Falha da KIE nunca impede a capa: o aviso diz se "repetir não adianta" (ajuste o prompt) ou se
  vale "tentar de novo mais tarde".
- Saídas: `<E>/capa.png` (1240x1754) e `<E>/mockup.png` (fundo transparente). Olhe as duas
  imagens e mostre ao aluno; refaça se ele pedir. O `mockup.png` serve para anúncios e posts (a
  página de vendas não tem espaço para ele). Slides, roteiros e planilhas não têm capa.
- Mudou título, subtítulo, autor ou paleta depois da capa pronta: rode `entregavel_capa` SEM --arte
  (reaproveita o `arte.png`) e só então o PDF; o PDF avisa se a capa ficou mais antiga que o
  `meta.json`.
- Com `--arte` e chave KIE, uma arte NOVA é gerada e substitui a atual (gasta crédito).

## Passo 5 — Gerar o PDF (ou a planilha)

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/03-entregaveis/scripts"; "$PY" "$S/entregavel_pdf.py" --pasta "<E>" --paleta '<paleta>' --carrossel "<P>/pagina/imagens/carrossel" --ordem 1
```

- Saídas: `<E>/<slug>.pdf` e `<E>/previa/amostra-1.png` e `amostra-2.png`: as 2 páginas de
  conteúdo mais visuais (com mais caixas, tabelas, checklists ou imagens; o sumário entra só
  se tiver 8 itens ou mais). Documento sem capítulos (`#`) usa as duas primeiras páginas do
  texto. Nos slides, as amostras são os slides 2 e 3.
- `--carrossel` copia pro carrossel da página de vendas as imagens `NN-<slug>-01.jpg` (a capa
  reduzida, se existir), `NN-<slug>-02.png`…, onde `NN` é o `--ordem` (1 a 99, padrão 50): o
  carrossel segue essa ordem. Use `--ordem 1` no produto principal, `--ordem 2` no primeiro
  bônus, `--ordem 3` no seguinte, e assim por diante. Só os arquivos deste entregável são
  substituídos; os outros do carrossel ficam. Omita `--carrossel` se o aluno não quiser. Slides: não use `--carrossel`.
  Roteiro não vai pro carrossel (o script pula a cópia e avisa).
- Se falhar, o PDF anterior é mantido. Erros comuns: `meta.json`/`conteudo.md` faltando, erro de
  formatação, arquivo que não está em UTF-8 (peça pra salvar como UTF-8).
- Olhe `previa/amostra-1.png` e `amostra-2.png` antes de mostrar ao aluno. Ele aprova; se pedir
  mudança, edite o `conteudo.md` e rode de novo.

Planilha (lê `planilha.json`, grava `<E>/<slug>.xlsx`, fórmulas recalculam ao abrir):

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/03-entregaveis/scripts"; "$PY" "$S/entregavel_planilha.py" --pasta "<E>"
```

## Passo 6 — Fechar

1. Confira que todo item do mapa virou arquivo (`<E>/<slug>.pdf` ou `.xlsx`).
2. Se algum título final mudou, registre com `maquina oferta adicionar` (os itens antigos não
   são removidos — avise o aluno).
3. Se a página de vendas já existe, monte de novo pro carrossel aparecer (o publicar do
   Sistema 02 também remonta):

```bash
PY="$HOME/.maquina/venv/bin/python"; S2="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S2/pagina_render.py" --projeto "<P>"
```

   Se a página já está no ar, publique de novo com o Sistema 02 para o carrossel novo aparecer
   pros clientes:

```bash
PY="$HOME/.maquina/venv/bin/python"; S2="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S2/pagina_publicar.py" --projeto "<P>"
```

4. Diga onde estão os arquivos pra subir na área de membros (Kiwify, Hotmart, Payt…).
