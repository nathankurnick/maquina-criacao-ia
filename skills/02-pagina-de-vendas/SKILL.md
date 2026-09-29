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
(paleta, pixels, SEO), `scripts/pagina_publicar.py` (Netlify). Referência de copy:
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
prévia, mas não publicar. Grave com `link_checkout='https://...'`.

Se existir `<P>/pesquisa/escolhida.json`, leia o `pasta_oferta` dele e o `dissecacao.md` dessa
pasta: use a estrutura que vende, nunca as frases do concorrente.

## Passo 2 — Escrever a copy

Siga `referencias/copy.md` e escreva `<P>/pagina/conteudo.json` (crie a pasta `pagina` se não
existir). Mostre ao aluno um resumo: headline, subheadline, os 5 itens do conteúdo, bônus,
preço e garantia, e peça a aprovação dele antes de seguir. Ajuste o que ele pedir, bloco por
bloco (edite só aquele bloco no JSON).

A IA não inventa prova (depoimento, nome de cliente, nota, número de alunos). Depoimento só
entra como print real do aluno (Passo 3).

## Passo 3 — Imagens (opcional)

Explique as pastas e deixe o aluno colocar os arquivos:

- `<P>/pagina/imagens/logo.png` — logo (png, jpg, webp ou svg).
- `<P>/pagina/imagens/carrossel/` — prints do material por dentro (páginas do ebook, telas).
- `<P>/pagina/imagens/depoimentos/` — **só prints de depoimentos reais**. Sem imagens, a seção
  fica escondida.

## Passo 4 — Paleta e pixels

Mostre as paletas e pergunte qual:

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_config.py" --projeto "<P>" --paletas
```

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_config.py" --projeto "<P>" --definir 'paleta=preto-dourado'
```

Pixels são opcionais: `--definir 'pixel_meta=<só números>'`, `--definir 'pixel_google=G-XXXX'`.
Código extra no `<head>` (Utmify etc.): salve o trecho que o aluno colar num arquivo e use
`--head-arquivo "<arquivo>"`. SEO: `--definir 'seo_titulo=...'` e `--definir 'seo_descricao=...'`.
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

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/02-pagina-de-vendas/scripts"; "$PY" "$S/pagina_publicar.py" --projeto "<P>"
```

- Saída 0 ("✅ No ar: <url>"): mostre o link. Se vier o aviso "⚠️ Não consegui salvar o endereço…",
  mostre também o link e o `site_id` e peça pro aluno anotar.  Mudanças depois: ajuste, monte (Passo 5) e publique de novo —
  o link continua o mesmo.
- Saída 3 (sem chave da Netlify): o script mostra o passo a passo do Netlify Drop
  (https://app.netlify.com/drop, arrastar a pasta `site`). Acompanhe o aluno e ofereça configurar a
  chave com `maquina chaves` pra próxima vez.
- Saída 1: mostre a mensagem (falta checkout, página não montada, chave recusada…) e resolva. Se
  disser "A Máquina não está instalada direito", peça pra rodar o `instalar.sh` de novo.
- Saída 130: o aluno cancelou; nada foi publicado.

## Regerar

Se o aluno atualizou a Máquina ou pediu "regerar a página", só rode os Passos 5 e 6 (sem
reescrever a copy): o
`conteudo.json` guarda a copy e o template novo é aplicado.
