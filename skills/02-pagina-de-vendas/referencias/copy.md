# Copy da página: formato do conteudo.json e como escrever cada bloco

Você escreve `<P>/pagina/conteudo.json` com este formato (12 blocos, na ordem da página).
Qualquer bloco pode ter `"ativo": false` pra ficar escondido. Trechos da headline entre
`**asteriscos duplos**` saem na cor de destaque.

O `checkoutUrl` do exemplo está vazio de propósito: use o `link_checkout` real do oferta.md.

```json
{
  "hero": {
    "badge": "MÉTODO PASSO A PASSO",
    "headline": "Aprenda a fazer **pão caseiro macio** na primeira tentativa",
    "subheadline": "Receitas testadas, com medidas exatas e vídeo de cada etapa.",
    "cta": "QUERO APRENDER AGORA"
  },
  "carrossel": { "titulo": "Veja o material por dentro", "descricao": "Uma olhada nas páginas." },
  "paraQuem": {
    "titulo": "Pra quem é",
    "subtitulo": "Se você se vê aqui, é pra você.",
    "itens": [
      { "titulo": "Quem nunca fez pão", "descricao": "Começa do zero, sem termo difícil." },
      { "titulo": "Quem já tentou e não deu certo", "descricao": "Entende onde errava." },
      { "titulo": "Quem quer vender", "descricao": "Receitas com rendimento calculado." }
    ]
  },
  "conteudo": {
    "titulo": "O que você vai encontrar",
    "subtitulo": "Tudo organizado do básico ao avançado.",
    "itens": [
      { "icone": "livro", "titulo": "Receitas base", "descricao": "As 5 massas que resolvem tudo.", "imagem": "massas.jpg" },
      { "icone": "relogio", "titulo": "Tempo de fermentação", "descricao": "Tabela pra cada clima.", "arte": "Rustic homemade bread dough rising in a glass bowl on a wooden kitchen table" },
      { "icone": "lista", "titulo": "Lista de compras", "descricao": "O que comprar e onde." },
      { "icone": "ferramenta", "titulo": "Utensílios", "descricao": "O mínimo que você precisa." },
      { "icone": "estrela", "titulo": "Recheios", "descricao": "Doces e salgados." }
    ]
  },
  "incluso": {
    "titulo": "O que está incluído",
    "nota": "",
    "itens": [
      { "titulo": "Ebook de receitas", "descricao": "PDF pra ler no celular." },
      { "titulo": "Vídeos curtos", "descricao": "Cada etapa filmada." },
      { "titulo": "Tabela de fermentação", "descricao": "Pra imprimir." },
      { "titulo": "Lista de compras", "descricao": "Pronta." },
      { "titulo": "Guia de erros comuns", "descricao": "E como corrigir." }
    ]
  },
  "entrega": {
    "titulo": "Como você recebe",
    "subtitulo": "Sem complicação.",
    "itens": [
      { "icone": "raio", "titulo": "Acesso Imediato", "descricao": "Chega no seu e-mail logo após a compra." },
      { "icone": "cartao", "titulo": "Pagamento Único", "descricao": "Sem mensalidade." },
      { "icone": "infinito", "titulo": "Acesso Vitalício", "descricao": "Veja quando quiser." }
    ]
  },
  "bonus": {
    "titulo": "Bônus de hoje",
    "subtitulo": "Só pra quem entrar agora.",
    "itens": [
      { "titulo": "Planilha de custos", "descricao": "Calcule o preço de venda.", "valor": "R$47" }
    ]
  },
  "depoimentos": { "titulo": "Veja o que estão dizendo", "subtitulo": "" },
  "planos": {
    "titulo": "Escolha seu acesso",
    "subtitulo": "",
    "basico": {
      "nome": "ACESSO COMPLETO",
      "itens": ["Ebook de receitas", "Vídeos curtos", "Todos os bônus"],
      "precoDe": "",
      "precoPor": "R$ 27",
      "checkoutUrl": "",
      "cta": "QUERO MEU ACESSO"
    },
    "premium": { "ativo": false }
  },
  "garantia": {
    "titulo": "GARANTIA INCONDICIONAL",
    "dias": 7,
    "texto": "Se não gostar, peça o reembolso em até 7 dias e devolvemos 100% do valor.",
    "cta": "GARANTIR MEU ACESSO"
  },
  "faq": {
    "titulo": "Perguntas Frequentes",
    "itens": [
      { "pergunta": "Preciso de batedeira?", "resposta": "Não. Tudo é feito na mão." }
    ]
  },
  "rodape": { "nomeProduto": "Pão Fácil", "disclaimer": "" }
}
```

## De onde vem cada informação

- **oferta.md** (`maquina oferta mostrar <slug>`): nome, promessa, mecanismo, avatar, preço,
  entregáveis, bônus, garantia e link de checkout. Não crie entregável ou bônus que não esteja
  lá — se faltar algo, pergunte ao aluno e grave com
  `maquina oferta adicionar <slug> entregaveis|bonus '<item>'` (item que começa com "-": ponha
  `--` antes, ex.: `maquina oferta adicionar <slug> bonus -- '-30% no próximo curso'`).
- Não invente estudo, estatística ou citação; se precisar de um dado, escreva "confirme esta
  informação" e pergunte ao aluno.
- **Dissecação do Sistema 01** (se existir `<P>/pesquisa/escolhida.json` → `pasta_oferta/dissecacao.md`):
  use a ESTRUTURA que vende (ordem de argumentos, tipo de bônus, ancoragem), nunca as frases.

## Como escrever

- Português do Brasil, na língua do público: frases curtas, verbo forte, benefício antes de
  característica, sem jargão ("transforme sua realidade", "jornada").
- `hero.headline`: a promessa central; marque 2 a 4 palavras decisivas com `**`.
- `hero.cta` e todos os `cta`: CAIXA ALTA, até 5 palavras.
- `conteudo.itens`: 5 itens; `icone` só uma destas: livro, busca, estrela, camera, etiqueta,
  trofeu, ferramenta, lista, relogio, escudo, calculadora, documento, raio, cartao, infinito,
  mensagem, download, cadeado, presente, check.
- Foto no cartão (opcional, deixa a seção bem mais bonita): `"imagem": "<arquivo>"` usa uma foto
  que o aluno pôs em `pagina/imagens/conteudo/` (só o nome do arquivo: minúsculas, números e hífen,
  .png/.jpg/.webp); ou `"arte": "<descrição em inglês da cena, sem texto>"` faz o `pagina_mockups.py`
  gerar a foto na KIE (sem a chave, o cartão fica só com o ícone). `imagem` ganha da `arte`.
  Ou todos os cartões têm foto, ou nenhum (misturar fica desigual).
- `entrega.itens`: `icone` opcional (mesma lista); sem ele, vão raio, cartao e infinito, nessa ordem.
- `incluso.itens`: 5 itens reforçando o `conteudo` com outras palavras.
- `bonus.itens`: os bônus do oferta.md; `valor` é o valor de referência que o aluno confirmar.
- `faq.itens`: 6 perguntas; pelo menos 3 respondem às objeções mais fortes do avatar.
- `planos.basico.precoPor`: exatamente o preço do oferta.md. `precoDe` só se o aluno der um
  preço de âncora; senão deixe vazio (nunca invente).
- `planos.basico.checkoutUrl`: o `link_checkout` do oferta.md, que precisa ser o endereço real
  de pagamento e começar com `https://` (só https; o texto-modelo `SEU-LINK` não vale). Sem link
  real ainda → deixe `"checkoutUrl": ""` (a página monta pra prévia, mas não publica). Link
  inválido desliga o plano e o render avisa.
  Premium só se o aluno tiver um segundo link de checkout, diferente do básico.
- `garantia.dias`: o número de dias da garantia do oferta.md.
- `hero.entregavel` e `bonus.itens[].entregavel` (opcionais): nome da pasta do entregável em
  `<P>/entregaveis/` (só minúsculas, números e hífen). A capa dessa pasta vira o mockup da página.
- `rodape.disclaimer`: o aviso legal é padrão (deixe vazio e entra o texto padrão); se o aluno
  quiser tirar, use `"-"` (o rodapé fica só com a linha de direitos reservados).

## Prova

A IA não inventa depoimento, nome de cliente, print, nota ou número de alunos. A seção de
depoimentos só aparece quando o aluno coloca prints REAIS em `pagina/imagens/depoimentos/`.
Promessa, prazo e tom são decisão do aluno — escreva o que ele pedir.
