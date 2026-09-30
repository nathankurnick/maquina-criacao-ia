# Order bump

As 4 caixinhas marcáveis no checkout ("adicione também…"). Todo funil da Máquina tem 4 order bumps:
é a oferta mais fácil do funil, a pessoa já está com o cartão na mão.

- **O que oferecer:** algo pequeno que acelera ou facilita o produto principal (checklist,
  planilha, templates, versão em áudio, bônus de implementação). Deve fazer sentido em 1 linha. Os 4 precisam ser diferentes entre si — cada um resolve uma coisa
  (acelerar, organizar, facilitar, complementar).
- **Preço:** 20% a 50% do produto principal (ex.: front R$ 27 → bump R$ 9,90 a R$ 14,90).
- **Nome:** concreto e com benefício ("Lista de compras inteligente — economize 2 horas por semana").
- **Copy do checkout (até ~300 caracteres):** título + 1–2 frases do que é + por que agora
  ("só aparece aqui, com desconto de cliente"). Exemplo:
  > **SIM! Quero a Lista de compras inteligente por só R$ 9,90**
  > A lista pronta, separada por setor do mercado, com as quantidades exatas de cada receita.
- **Sem prova inventada:** não invente depoimento, número de alunos nem resultado na copy do bump.
- **Conteúdo (produto SEPARADO):** os bumps NÃO entram no produto principal. Escreva o conteúdo com as
  regras de formato e os scripts do Sistema 03, mas cada um dos 4 tem a própria pasta `<P>/funil/bump/entregaveis/<item>/` (passando
  `--pasta` para lá). Nunca use `maquina oferta adicionar` para os bumps e nunca `--carrossel`. O aluno
  sobe cada PDF na plataforma como um produto separado (são 4 produtos), ligado ao checkout como order bump.

A pasta do item precisa ter `meta.json` e `conteudo.md`, como no SKILL do Sistema 03. Rode a capa ANTES do PDF (o 03 só embute a `capa.png` se ela já existir).

```bash
PY="$HOME/.maquina/venv/bin/python"; S3="$HOME/.claude/skills/03-entregaveis/scripts"; "$PY" "$S3/entregavel_capa.py" --pasta "<P>/funil/bump/entregaveis/<item>" --paleta '<paleta>' --arte '<descrição visual, sem texto>'
```

```bash
PY="$HOME/.maquina/venv/bin/python"; S3="$HOME/.claude/skills/03-entregaveis/scripts"; "$PY" "$S3/entregavel_pdf.py" --pasta "<P>/funil/bump/entregaveis/<item>" --paleta '<paleta>'
```
