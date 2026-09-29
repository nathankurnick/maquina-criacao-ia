---
name: 05-funil
description: "Sistema 05 da Máquina Criação IA — Funil de Vendas. Monta o funil low ticket (anúncio → página → checkout com order bump → upsell → downsell → obrigado), projeta o ticket médio em código, cria bump, upsell e downsell pelo método Segredos do Upsell (oferta, nome, copy em 5 blocos), gera e publica as páginas de upsell/downsell, escreve e-mails e WhatsApp de recuperação e pós-compra, o checklist da plataforma e ideias de próximo produto. Use quando o aluno pedir /05-funil, 'montar o funil', 'order bump', 'upsell', 'downsell', 'página de obrigado', 'aumentar o ticket médio', 'recuperação de carrinho' ou 'e-mails pós-compra'."
---

# Sistema 05 — Funil de Vendas

Você monta o funil do aluno. Fale simples, um passo por vez, e pare nos CHECKPOINTS.

**Cada comando Bash é independente**: cole as definições no começo de cada comando, exatamente
como nos exemplos, e escreva `<P>` como caminho absoluto anotado antes. Valores do
`maquina oferta` sempre em aspas simples.

Scripts: `scripts/funil_mapa.py` (mapa + ticket médio), `scripts/funil_oto.py` (páginas de
upsell/downsell). Método de upsell: `referencias/upsell/metodologia.md`,
`referencias/upsell/copy-5-blocos.md`, `referencias/upsell/caso-exemplo.md`. Outras
referências: `referencias/order-bump.md`, `referencias/mensagens.md`, `referencias/plataformas.md`.

## Passo 1 — O que já existe

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto listar
```

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto caminho <slug>; "$M" oferta mostrar <slug>
```

Anote `<P>` e leia a oferta que o `maquina oferta mostrar` imprimiu (JSON). Leia também, se
existirem: `<P>/pagina/conteudo.json` (preço e promessa NO AR), `<P>/pagina/config.json`
(`paleta`, `url`) e a lista de `<P>/entregaveis/`. Leia `referencias/upsell/metodologia.md` e
`referencias/upsell/caso-exemplo.md` antes de propor qualquer upsell.

## Passo 2 — Esteira de ofertas ✋ CHECKPOINT

Pela pergunta-mestra do método ("qual é a próxima etapa lógica?"), proponha:

- **Order bump** (`referencias/order-bump.md`): 20–50% do preço do produto principal.
- **Upsell** ⭐: 2–4 ideias nos 3 tipos (mais do mesmo / resultados mais rápidos / done for you),
  cada uma com problema que resolve, congruência com o produto principal e ticket de 2,5–3,5×.
- **Downsell**: versão menor/mais barata do upsell pra quem recusou.

Pare e espere o aluno escolher. Depois grave `<P>/funil/funil.json` (crie a pasta `funil`):

```json
{"front":    {"nome": "Marmitas Já", "preco": 27},
 "bump":     {"nome": "Lista de compras inteligente", "preco": 9.9, "conversao": 0.3},
 "upsell":   {"nome": "Cardápio 30 dias", "preco": 67, "conversao": 0.15},
 "downsell": {"nome": "Cardápio 15 dias", "preco": 37, "conversao": 0.15}}
```

Regras dos números (o script confere e rejeita o que não entende):

- `preco`: aceita `27`, `"R$ 27,90"` ou `"1.297,00"`. Preço parcelado (`"12x de…"`) é
  rejeitado: use o valor à vista.
- `conversao` é opcional (sem ela, usa o meio da faixa de referência). Escreva `0.3`, `"30%"`
  ou `"1%"`. O valor `1` puro é rejeitado por ser ambíguo (1% ou 100%?): escreva `"1%"` ou
  `0.01` para 1%, `"100%"` para 100%.
- O downsell só existe se houver upsell.

Desenhe o mapa (a paleta vem do argumento `--paleta`, senão do `pagina/config.json`, senão do
`oferta.md`, senão `azul-laranja`):

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/05-funil/scripts"; "$PY" "$S/funil_mapa.py" --projeto "<P>"
```

Abra e mostre `<P>/funil/mapa.png` (e, se quiser, o `mapa.html` ao lado) e o ticket médio
projetado. O resumo do mapa classifica o aumento sobre o produto principal: abaixo de 25% é
"abaixo da meta"; de 25% a 30% é "dentro da meta"; acima de 30% é "acima da meta" e o mapa pede
para conferir se as conversões não estão otimistas. Conversão fora da faixa de referência de
mercado ganha o aviso "⚠️ fora da referência" ao lado da caixa da oferta. Os números são
referência — o aluno troca pelos dele quando tiver dados. Saída 0: ok. Saída 1: mostre a
mensagem e corrija o `funil.json`. Saída 130: o aluno cancelou (Ctrl+C), sem problema.

## Passo 3 — Order bump

Escreva `<P>/funil/order-bump.md` (nome, preço, copy do checkout). O conteúdo do bump é
produzido no Sistema 03 (`/03-entregaveis`) como um bônus.

## Passo 4 — Upsell (e downsell) pelo método ✋ CHECKPOINTS

Siga o método em `referencias/upsell/metodologia.md`:

1. **Nome** ✋: 12–17 nomes por ângulo, 3 apostas justificadas; espere a aprovação.
2. **Definição**: mecanismo nomeado, entregáveis, bônus que mata a maior objeção, garantia
   (igual ou maior que a do produto principal), história de criação e 3 preços pra teste.
   A história usa **relato real** que o aluno contar; se não houver, use a lacuna entre saber e
   executar. A IA não inventa relato, depoimento, número de alunos nem resultado.
3. **Copy dos 5 blocos** ✋ (`referencias/upsell/copy-5-blocos.md`) em `<P>/funil/upsell/roteiro.md`
   (vídeo: roteiro pra gravar e subir no VTurb/YouTube; ou texto). Espere a revisão.
4. **Conteúdo do upsell**: produza no Sistema 03 (`/03-entregaveis`).

Página do upsell — escreva `<P>/funil/upsell/oto.json`:

```json
{"formato": "video", "video": "<link do YouTube/Vimeo ou o código do player do VTurb>",
 "checkout_url": "<link de pagamento do upsell na plataforma>", "atraso_segundos": 0,
 "recusar_url": "<link da página de downsell ou de obrigado>"}
```

- `pre_headline`, `headline`, `copy_abaixo`, `botao_texto`, `recusar_texto` já vêm com o texto
  do método; só inclua se quiser mudar.
- `formato: "texto"` + campo `texto` (parágrafos separados por linha em branco) pra upsell em texto.
- `botao_html`: se a plataforma der um botão de compra em 1 clique, cole o código aqui (aí o
  `checkout_url` não é obrigatório).
- `atraso_segundos`: o botão aparece depois desse tempo (o método sugere ~60–70% do vídeo quando
  o objetivo é ticket médio). Se o player (VTurb) já controla o botão, deixe 0.

O comando sempre monta a pasta `site/` (`<P>/funil/upsell/site/index.html`); só publica com
`--publicar`. Monte, olhe e publique:

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/05-funil/scripts"; "$PY" "$S/funil_oto.py" --pasta "<P>/funil/upsell" --paleta '<paleta>'
```

```bash
open "<P>/funil/upsell/site/index.html"
```

Aviso: abrindo o arquivo direto do computador, o vídeo do YouTube/Vimeo NÃO toca na prévia
(o navegador bloqueia o player em arquivo local). Ele passa a tocar depois de publicado. Avise o
aluno antes, para ele não achar que quebrou; confira o resto (textos, botão, cores) na prévia.

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/05-funil/scripts"; "$PY" "$S/funil_oto.py" --pasta "<P>/funil/upsell" --paleta '<paleta>' --publicar
```

- Saída 0: anote o link "No ar" — ele vai na plataforma como página depois da compra. Se
  aparecer "⚠️ O endereço mudou", o link antigo deixou de valer: o aluno precisa atualizar o
  link na plataforma.
- Saída 3 (sem chave da Netlify): a página já foi montada; siga as instruções impressas. Sem
  endereço salvo: entrar (ou criar conta) na Netlify ANTES, senão a página some em cerca de 1
  hora; abrir app.netlify.com/drop e arrastar a pasta `site`; copiar o link e mandar pra você.
  Se a página já tem endereço salvo, o script avisa para atualizar SEM mudar o endereço: abrir o
  site na Netlify, aba Deploys, e arrastar a pasta `site` lá. O aluno roda `maquina chaves` no
  Terminal dele se quiser publicar sozinho (é interativo).
- Saída 1: mostre a mensagem (link de compra inválido, vídeo não reconhecido…) e corrija.
- Saída 130: o aluno cancelou (Ctrl+C).

Downsell: repita tudo em `<P>/funil/downsell/` (oferta menor, mesma estrutura de página). O
`recusar_url` do upsell aponta pro link do downsell.

## Passo 5 — Mensagens

Siga `referencias/mensagens.md` e escreva `<P>/funil/mensagens.md` (carrinho abandonado,
boleto/PIX, pós-compra). Use os links reais (checkout, área de membros).

## Passo 6 — Checklist da plataforma

Pergunte qual plataforma o aluno usa e escreva `<P>/funil/checklist.md` a partir de
`referencias/plataformas.md`, já com os links dele (página, upsell, downsell). Explique o teste
com uma compra real de valor baixo.

## Passo 7 — Fidelizar

Escreva `<P>/funil/proximos-produtos.md` com 2–3 ideias de próximo produto ou recorrência
(congruentes com o que o aluno já vende). Cada ideia pode virar um projeto novo no
`/01-pesquisa-ofertas`.
