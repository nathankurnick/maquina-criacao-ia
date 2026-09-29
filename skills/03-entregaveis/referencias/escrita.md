# Como escrever os entregáveis

- Conteúdo de verdade, completo: nada de sumário vazio ou "neste capítulo você vai aprender".
  O aluno vai vender isso.
- Português do Brasil, frases curtas, na língua do público. Exemplos concretos do nicho.
- Material grande (ebook, roteiro de curso): escreva capítulo por capítulo e mostre ao aluno
  antes de seguir.
- Não invente estudo, estatística, citação, depoimento ou resultado de cliente. Faltou estudo,
  número ou citação: escreva "(confirme esta informação)" e pergunte ao aluno. Faltou prova
  (depoimento, resultado de cliente): escreva "[cole aqui um depoimento real]".
- Nicho de saúde, dinheiro ou corpo: inclua um aviso curto de que o material é educacional e
  não substitui um profissional (o aluno pode pedir pra tirar).
- Salve `conteudo.md` e `meta.json` em UTF-8 (o gerador recusa outra codificação).

## O Markdown que o gerador entende

```markdown
# Capítulo 1 — Começando do jeito certo

Parágrafo normal com **negrito**, *itálico* e um link [assim](https://exemplo.com).

## O que você precisa

- Farinha de trigo
- Fermento seco

1. Misture os secos
2. Adicione a água aos poucos

> **Dica:** use água morna, nunca quente.

> **Atenção:** não pule o descanso da massa.

- [ ] Separei os ingredientes
- [ ] Deixei a massa descansar

| Ingrediente | Quantidade |
|---|---|
| Farinha | 500 g |
| Água | 300 ml |

![Massa pronta](imagens/massa.png)
```

- `#` = capítulo (começa página nova e entra no sumário); `##` = seção (entra no sumário); `###` = subtítulo.
- Caixas: `> **Dica:**`, `> **Atenção:**`, `> **Exemplo:**`, `> **Importante:**` (ou só `>`).
  Cada caixa é um parágrafo só (uma linha `>` em branco já encerra a caixa).
- Imagens: coloque o arquivo em `imagens/` dentro da pasta do entregável, com nome em
  minúsculas, sem acento, com hífens e até ~1600 px de largura.
- Slides: separe cada slide com uma linha só com `---`.
