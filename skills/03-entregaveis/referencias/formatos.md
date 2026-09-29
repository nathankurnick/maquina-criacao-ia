# Qual formato pra cada entregável

Escolha o formato que entrega mais valor percebido com menos esforço pro aluno produzir.

| Formato (`tipo`) | Quando usar | Tamanho típico |
|---|---|---|
| `ebook` | Produto principal que ensina um método do começo ao fim | 25–60 páginas, 5–10 capítulos |
| `guia` | Bônus prático e direto (passo a passo de uma tarefa) | 8–20 páginas |
| `checklist` | Bônus de execução: o aluno marca o que já fez | 2–6 páginas |
| `roteiro` | Curso em vídeo: roteiro de cada aula pro aluno gravar | 1 capítulo por aula |
| `slides` | Apoio visual das aulas gravadas | 8–20 slides por aula |
| `planilha` | Planner, controle, cardápio, calculadora | 1–4 abas |

## Estrutura de cada um

**ebook** — Introdução (o problema e a promessa) → capítulos na ordem em que o aluno aplica
→ capítulo final de "próximos passos". Cada capítulo: por que importa, passo a passo,
exemplo, erro comum, caixa de dica.

**guia** — O que você vai conseguir → o que precisa → passos numerados → erros comuns → checklist final.

**checklist** — Agrupado por fase (antes / durante / depois), itens começando com verbo.

**roteiro** — Um `#` por aula: objetivo da aula, abertura (gancho em 1 frase), tópicos com o
que falar, exemplo, fechamento com tarefa. Escreva como a pessoa fala.

**slides** — Um slide por ideia; título curto + no máximo 4 tópicos. Separe slides com `---`.

**planilha** — Uma aba por finalidade; colunas com nome claro; exemplo preenchido nas
primeiras linhas; fórmulas começando com `=`, recalculadas quando a planilha é aberta.
Fórmulas sempre em **inglês e com vírgula**: `=SUM(C2:C31)`, `=IF(A2>0,1,0)` (o script recusa
`SOMA`, `SE`, `PROCV`, `MÉDIA`, `CONT.SE`, `SOMASE` e `;`, e diz o nome certo). Números entram como
números do JSON. Por aba, `"formatos"` opcional, um por coluna: `"texto"`, `"numero"`, `"moeda"`
(R$ 1.234,50), `"percentual"` (0,25 vira 25%) ou `"data"` (aceita `"2026-10-01"`).
