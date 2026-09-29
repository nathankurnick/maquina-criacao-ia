# Ângulos, copys e roteiros

## De onde vêm os ângulos

1. `<P>/pesquisa/escolhida.json` → `pasta_oferta/dissecacao.md`, seção "Ângulos de hook": os
   ângulos que o concorrente escalou, com o anúncio de exemplo.
2. `pasta_oferta/anuncios/criativos.json`: textos dos anúncios vencedores e as imagens/vídeos
   baixados (olhe as imagens; dos vídeos, use o texto).
3. A oferta do aluno (`maquina oferta mostrar`): promessa, mecanismo, avatar, dores.

Monte 5 ângulos diferentes (dor, desejo, mecanismo/novidade, objeção quebrada, prova do
processo). A referência é a ESTRUTURA do vencedor — nunca as frases dele.

## Anúncio estático

- `headline_imagem`: até 8 palavras, a ideia central do ângulo; marque 1–3 palavras com `**`.
- `texto_principal`: 3–6 linhas curtas: gancho → problema/desejo → o que o produto entrega →
  convite. Emoji com moderação.
- `titulo`: até 40 caracteres (aparece abaixo da imagem).
- `descricao`: opcional, uma frase.
- `cta`: um destes botões da Meta: Saiba mais, Comprar agora, Cadastre-se, Enviar mensagem, Ver mais, Baixar.
- `visual.prompt`: só descrição visual da cena (sem texto na imagem): assunto, cenário, luz, cores.
- `visual.produto`: nome da pasta do entregável em `<P>/entregaveis/` cujo `mockup.png` entra na arte (ou vazio).
- `visual.layout`: `base` (produto em cima, frase embaixo), `topo` (frase em cima) ou `centro` (só frase).

## Anúncio em vídeo (1 corpo × N hooks)

- `hooks`: 3 a 5 começos diferentes (os primeiros 3 segundos), cada um num ângulo.
- `corpo`: 30–45 segundos falados: problema → virada (mecanismo) → o que a pessoa recebe.
- `cta_falado`: a frase final ("toca em saiba mais e…").
- `cenas`: o que aparece na tela em cada trecho (o aluno grava com o celular).
- `texto_principal`, `titulo` e `cta` também são obrigatórios (vão no Gerenciador).

## Coerência com a página

O anúncio promete o que a página entrega. Se a página é paga, nunca diga "grátis". Preço e
bônus só se estiverem na oferta. A IA não inventa prova, número de alunos, estudo nem estatística.

## Exemplo do anuncios.json

```json
{"anuncios": [
  {"id": "dor-cozinha", "angulo": "Cansaço de cozinhar todo dia", "formato": "estatico",
   "headline_imagem": "Comida pronta pra **15 dias**",
   "texto_principal": "Chega em casa sem energia pra cozinhar?\nCom o método de marmitas você prepara tudo num domingo.\nReceitas, lista de compras e como congelar.",
   "titulo": "Marmitas pra 15 dias", "descricao": "Receitas testadas", "cta": "Saiba mais",
   "visual": {"prompt": "marmitas coloridas em potes de vidro sobre bancada clara, luz natural", "produto": "", "layout": "base"}},
  {"id": "video-rotina", "angulo": "Rotina corrida", "formato": "video",
   "hooks": ["Se você chega em casa sem energia pra cozinhar, olha isso.", "Eu cozinho uma vez e como bem por 15 dias."],
   "corpo": "Eu vivia pedindo delivery…", "cta_falado": "Toca em saiba mais e veja as receitas.",
   "cenas": ["Geladeira cheia de marmitas", "Montando os potes"],
   "texto_principal": "Uma tarde de domingo, 15 dias de comida pronta.", "titulo": "Marmitas pra 15 dias", "cta": "Saiba mais"}
]}
```
