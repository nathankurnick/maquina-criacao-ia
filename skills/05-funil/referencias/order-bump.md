# Order bump

A caixinha marcável no checkout ("adicione também…"). É a oferta mais fácil do funil: a pessoa
já está com o cartão na mão.

- **O que oferecer:** algo pequeno que acelera ou facilita o produto principal (checklist,
  planilha, templates, versão em áudio, bônus de implementação). Deve fazer sentido em 1 linha.
- **Preço:** 20% a 50% do produto principal (ex.: front R$ 27 → bump R$ 9,90 a R$ 14,90).
- **Nome:** concreto e com benefício ("Lista de compras inteligente — economize 2 horas por semana").
- **Copy do checkout (até ~300 caracteres):** título + 1–2 frases do que é + por que agora
  ("só aparece aqui, com desconto de cliente"). Exemplo:
  > **SIM! Quero a Lista de compras inteligente por só R$ 9,90**
  > A lista pronta, separada por setor do mercado, com as quantidades exatas de cada receita.
- **Sem prova inventada:** não invente depoimento, número de alunos nem resultado na copy do bump.
- **Conteúdo (produto SEPARADO):** o bump NÃO entra no produto principal. Escreva o conteúdo com as
  regras de formato e os scripts do Sistema 03, mas em `<P>/funil/bump/entregaveis/<item>/` (passando
  `--pasta` para lá). Nunca use `maquina oferta adicionar` para o bump e nunca `--carrossel`. O aluno
  sobe o PDF na plataforma como um produto separado, ligado ao checkout como order bump.

```bash
PY="$HOME/.maquina/venv/bin/python"; S3="$HOME/.claude/skills/03-entregaveis/scripts"; "$PY" "$S3/entregavel_pdf.py" --pasta "<P>/funil/bump/entregaveis/<item>" --paleta '<paleta>'
```

```bash
PY="$HOME/.maquina/venv/bin/python"; S3="$HOME/.claude/skills/03-entregaveis/scripts"; "$PY" "$S3/entregavel_capa.py" --pasta "<P>/funil/bump/entregaveis/<item>" --paleta '<paleta>' --arte '<descrição visual, sem texto>'
```
