---
name: 02-pagina-de-vendas
description: "Sistema 02 da Máquina Criação IA — Página de Vendas. Escreve a copy dos 12 blocos do template a partir do oferta.md do aluno (e da oferta dissecada no Sistema 01), monta o site na pasta do projeto, mostra a prévia no celular e publica na conta Netlify do aluno. Use quando o aluno pedir /02-pagina-de-vendas, 'criar minha página de vendas', 'montar a página', 'publicar a página', 'mudar a headline/cor da página' ou 'regerar a página'."
---

# Sistema 02 — Página de Vendas

Você cria a página de vendas do aluno com o template da Máquina. Fale simples, um passo por vez.

**Cada comando Bash é independente** (variáveis não passam de um comando pro outro): cole as
definições no começo de cada comando, exatamente como nos exemplos, e escreva as pastas
(`<P>`) como caminhos absolutos que você anotou antes. Valores do `maquina oferta definir` vão
sempre em aspas simples (apóstrofo dentro do valor vira `'\''`).

Scripts desta skill: `scripts/pagina_render.py` (monta o site), `scripts/pagina_config.py`
(paleta, pixels, SEO), `scripts/pagina_mockups.py` (gera os mockups),
`scripts/pagina_publicar.py` (Netlify). Referência de copy:
`referencias/copy.md`. Visual: `template/pagina.css`.

## Passo 1 — Projeto e oferta

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto listar
```

Pergunte qual projeto (ou crie com `"$M" projeto novo '<nome>'`) e pegue o caminho:

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto caminho <slug>; "$M" oferta mostrar <slug>; "$M" oferta faltando <slug>
```

Anote o caminho como `<P>` e leia a oferta que o `maquina oferta mostrar` imprimiu (o `oferta.md` só se mexe por esses comandos). Se `faltando` listar campos, pergunte só esses ao aluno e grave:

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta definir <slug> promessa='...' preco='R$ 27'
```

Confirme também o **link de checkout** (Kiwify, Hotmart, Payt…), que precisa começar com
`https://`. Sem ele (ou com link inválido), o plano fica desligado: dá pra montar e ver a
prévia, mas não publicar. Grave com `link_checkout='https://...'`. Se o link mudar depois,
atualize os dois lugares — `maquina oferta definir <slug> link_checkout='…'` e
`planos.basico.checkoutUrl` no `conteudo.json` — e publique de novo (Passo 6).

Se existir `<P>/pesquisa/escolhida.json`, leia o `pasta_oferta` dele e o `dissecacao.md` dessa
pasta: use a estrutura que vende, nunca as frases do concorrente.

## Passo 2 — Escrever a copy

Siga `referencias/copy.md` e escreva `<P>/pagina/conteudo.json` (crie a pasta `pagina` se não
existir). Mostre ao aluno um resumo: headline, subheadline, os 5 itens do conteúdo, bônus,
preço e garantia, e peça a aprovação dele antes de seguir. Ajuste o que ele pedir, bloco por
bloco (edite só aquele bloco no JSON).

A IA não inventa prova (depoimento, nome de cliente, nota, número de alunos). Depoimento só
entra como print real do aluno (Passo 3).

## Passo 3 — Imagens e mockups

Pastas que o aluno pode preencher:

- `<P>/pagina/imagens/logo.png` — logo (png, jpg, webp ou svg).
- `<P>/pagina/imagens/carrossel/` — páginas do material por dentro. O Sistema 03 já coloca aqui as
  2 páginas mais visuais de cada entregável; o aluno pode trocar ou acrescentar (máx. 6 aparecem).
- `<P>/pagina/imagens/depoimentos/` — **só prints de depoimentos reais**. Sem imagens, a seção
  fica escondida.

Ligue a copy aos entregáveis do Sistema 03 (pastas em `<P>/entregaveis/`): no `conteudo.json`, ponha
`"entregavel": "<pasta do produto principal>"` em `hero` e `"entregavel": "<pasta do bônus>"` em cada
item de `bonus.itens` que tiver pasta. Bônus sem pasta ganha uma capa simples com o título.

Veja o que vai ser gerado e quanto custa:

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_mockups.py" --projeto "<P>" --estimar
```

Mostre a estimativa ao aluno e peça o ok antes de gastar crédito da KIE. Com o ok:

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_mockups.py" --projeto "<P>"
```

Se ele não quiser gastar crédito, use `--sem-kie` (tudo montado por código, grátis). Pra gerar de novo
algo que já saiu (ex.: não gostou do mockup da KIE), use `--refazer`. O que não mudou não é cobrado de
novo. Saída 0 mesmo quando a KIE falha: os avisos dizem quais saíram no modo código e por quê.
Saída 1 = `conteudo.json` ausente/quebrado ou falha ao montar (a mensagem diz).

Sempre que o aluno trocar imagens do carrossel, capas do 03 ou bônus, rode o `pagina_mockups.py`
de novo antes de montar a página.

## Passo 4 — Paleta e pixels

Mostre as paletas e pergunte qual:

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_config.py" --projeto "<P>" --paletas
```

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_config.py" --projeto "<P>" --definir 'paleta=preto-dourado'
```

Grave a paleta também na oferta (fonte única de verdade):

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" oferta definir <slug> paleta='<escolhida>'
```

Pixels são opcionais: `--definir 'pixel_meta=<só números>'`, `--definir 'pixel_google=G-XXXX'`.
Código extra no `<head>` (Utmify etc.): salve o trecho que o aluno colar em `<P>/pagina/head.html`
(fora da pasta `site/`, que é recriada a cada montagem) e use `--head-arquivo "<P>/pagina/head.html"`. SEO: `--definir 'seo_titulo=...'` e `--definir 'seo_descricao=...'`.
Saída 1 = valor inválido (a mensagem diz o certo); nada é gravado. Saída 130 = cancelado.

## Passo 5 — Montar e ver a prévia

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_render.py" --projeto "<P>"
```

- Saída 0 ("✅ Página montada"): mostre os ⚠️ avisos (blocos escondidos e por quê, link de checkout
  inválido, sem imagens de depoimentos/carrossel) e resolva o que o aluno quiser.
- Saída 1: mostre a mensagem (JSON quebrado, `conteudo.json` ausente, `config.json` quebrado,
  falha ao gravar) e corrija. Se a montagem falhar, o site anterior continua intacto.

Abra a prévia pro aluno e confira você mesmo como fica no celular:

```bash
open "<P>/pagina/site/index.html"
```

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S/capturar.py" --url "file://<P>/pagina/site/index.html" --saida "<P>/pagina/previa"
```

Olhe `<P>/pagina/previa/dobra.png` (primeira tela) e as fatias `pagina-NN.png` (página inteira). Se algo estiver estranho
(texto enorme, bloco vazio), ajuste a copy e monte de novo.

## Passo 6 — Publicar

Publicar sempre remonta a página antes (o que vai ao ar é o `conteudo.json` e o `config.json`
de agora). Então qualquer edição, de copy ou de configuração, se publica só rodando este passo
de novo.

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_publicar.py" --projeto "<P>"
```

- Saída 0 ("✅ No ar: <url>"): mostre o link e os ⚠️ avisos de montagem. Se vier o aviso
  "⚠️ Não consegui salvar o endereço…", mostre também o link e o `site_id` e peça pro aluno
  anotar. Se vier "⚠️ O endereço da página mudou", avise que os links dos anúncios precisam ser
  atualizados. Mudanças depois: ajuste e rode este passo de novo — o link continua o mesmo.
- Saída 3 (sem chave da Netlify): o script mostra o passo a passo do Netlify Drop. Abra a pasta
  pro aluno achar (com `--pagina`, abra essa pasta) e acompanhe cada passo (entrar ou criar a conta grátis ANTES de arrastar: sem
  login a página é apagada em cerca de 1 hora):

  ```bash
  open "<P>/pagina"
  ```

  Se a página já tem endereço (`url` gravada), o script manda atualizar pela aba Deploys do site
  na Netlify (arrastar no Drop criaria um endereço novo). Quando o aluno mandar o link, grave-o:

  ```bash
  PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_config.py" --projeto "<P>" --definir 'url=https://...'
  ```

  Avise: se depois ele passar a publicar com a chave, a página ganha um endereço NOVO e os
  anúncios precisam ser atualizados. Se ele vai continuar editando a página, recomende
  configurar a chave agora: o aluno roda `maquina chaves` no Terminal dele (é interativo — não rode pelo Bash).
- Saída 1: mostre a mensagem (falta checkout, falha ao montar, chave recusada…) e resolva. Se
  disser "A Máquina não está instalada direito", peça pra rodar o `instalar.sh` de novo.
- Saída 130: o aluno cancelou; nada foi publicado.

## Regerar

Se o aluno atualizou a Máquina ou pediu "regerar a página", só rode os Passos 5 e 6 (sem
reescrever a copy): o `conteudo.json` guarda a copy e o template novo é aplicado.

## Outra página no mesmo projeto (ex.: upsell do Sistema 05)

Cada página vive na sua pasta, por exemplo `<P>/funil/upsell`, com o próprio `conteudo.json`,
`imagens/`, `config.json` e `site/`. O link de checkout vem do que o aluno informar para aquela
oferta (não é o `link_checkout` do oferta.md). Todo comando dos Passos 4 a 6 leva
`--pagina "<pasta>"` depois do `--projeto`, e a prévia abre `<pasta>/site/index.html`.
