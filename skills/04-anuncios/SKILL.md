---
name: 04-anuncios
description: "Sistema 04 da Máquina Criação IA — Anúncios. Usa os anúncios vencedores raspados no Sistema 01, a oferta e a página do Sistema 02 pra escrever anúncios estáticos em 5 ângulos e roteiros de vídeo (1 corpo × vários hooks), avisa riscos de reprovação na Meta (sem bloquear), monta as imagens 1:1 e 9:16 com o mockup do produto e exporta textos, roteiros e o plano de teste. Use quando o aluno pedir /04-anuncios, 'criar anúncios', 'criativos', 'copy dos ads', 'roteiro de vídeo pra anúncio' ou 'plano de teste'."
---

# Sistema 04 — Anúncios

Você cria os anúncios do aluno. Fale simples, um passo por vez, sem termos técnicos. O aluno
aprova os textos antes de você montar as imagens.

**Cada comando Bash é independente**: cole as definições no começo de cada comando, exatamente
como nos exemplos, e troque `<P>` (pasta do projeto) por caminho absoluto, entre aspas. Valores
do `maquina oferta` e textos do aluno sempre em aspas simples (apóstrofo vira `'\''`).

Scripts: `scripts/anuncio_riscos.py` (avisos da Meta), `scripts/anuncio_criativo.py` (imagens),
`scripts/anuncio_exportar.py` (textos, roteiros e plano). Referências: `referencias/angulos.md`
(como escrever e o formato do `anuncios.json`), `referencias/meta.md` (versões mais seguras).
Visual das imagens: `template/criativo.css`.

Códigos de saída dos scripts do 04: 0 (ok), 1 (problema previsto: leia a mensagem em português,
mostre ao aluno e corrija) ou 130 (cancelado). Nunca mostre erro técnico ao aluno.

## Passo 1 — Projeto, oferta e página

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto listar
```

Se houver mais de um, pergunte qual. Depois:

```bash
M="$(command -v maquina || echo "$HOME/.local/bin/maquina")"; "$M" projeto caminho <slug>; "$M" oferta mostrar <slug>
```

Anote `<P>` e leia a oferta que o `maquina oferta mostrar` imprimiu (JSON). Leia
`<P>/pagina/config.json` se existir: `url` é o link de destino e `paleta` a paleta da página.
Paleta, nesta ordem: a `paleta` do `pagina/config.json`; senão a `paleta` da oferta; se ambas
estiverem vazias, `azul-laranja`. O `anuncio_criativo.py` já lê o `config.json` sozinho quando você
não passa `--paleta`; passe `--paleta` só quando a paleta vier da oferta ou o aluno quiser outra.
Leia também `<P>/pagina/conteudo.json` se existir: promessa, preço, bônus e garantia que estão
NO AR. Os anúncios têm que bater com a página publicada (não prometa nada que ela não entrega).
Sem `url`, avise que a página ainda não está no ar (dá pra seguir e completar o link depois: o
exportar avisa e você roda de novo depois de publicar no Sistema 02).

## Passo 2 — Padrões dos vencedores

Se existir `<P>/pesquisa/escolhida.json`, leia o `pasta_oferta` dele e, lá dentro,
`dissecacao.md` (ângulos de hook) e `anuncios/criativos.json` (textos; olhe as imagens baixadas).

Sem `escolhida.json`, procure `<P>/pesquisa/oferta-*/dissecacao.md` (use o mais recente):
```bash
ls -dt "<P>"/pesquisa/oferta-*/dissecacao.md 2>/dev/null | head -1
```
Se achar, leia e use os ângulos dele (e o `anuncios/criativos.json` da mesma pasta, se houver).

Só se não houver nenhuma pesquisa, ofereça uma raspagem rápida do nicho com o Sistema 01 (1–2 minutos, abre o
Chrome). Use uma pasta NOVA a cada pesquisa (o `raspar.py` apaga o `anuncios.json` e o
`busca.json` que já estiverem nela):

```bash
PY="$HOME/.maquina/venv/bin/python"; S1="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S1/raspar.py" --termo '<nicho>' --rolagens 10 --saida "<P>/pesquisa/<AAAA-MM-DD>-<nicho-em-slug>"
```

Saídas do `raspar.py`: 0 = ok, siga; 1 = problema (mostre a mensagem ao aluno); 2 = nenhum anúncio
encontrado (siga só com a oferta, sem insistir); 130 = cancelado. Se o `raspar` sugerir o modo
manual, ignore a sugestão e continue com a oferta. Se saiu 0:

```bash
PY="$HOME/.maquina/venv/bin/python"; S1="$HOME/.claude/skills/01-pesquisa-ofertas/scripts"; "$PY" "$S1/ofertas.py" "<P>/pesquisa/<AAAA-MM-DD>-<nicho-em-slug>/anuncios.json" --saida "<P>/pesquisa/<AAAA-MM-DD>-<nicho-em-slug>"
```

`ofertas.py` com código 2 = nenhuma oferta agrupada (siga só com a oferta); 1 = problema. Fora
isso, use os `textos` das ofertas do topo do `ofertas.json`. Se o aluno não quiser pesquisar, siga
só com a oferta.

## Passo 3 — Escrever os anúncios

Siga `referencias/angulos.md` e escreva `<P>/anuncios/anuncios.json` com 5 estáticos (um por
ângulo) e 1–2 vídeos (3–5 hooks cada). Regras:

- O anúncio promete o que a página entrega; se a página é paga, nunca "grátis".
- A IA não inventa prova, número de alunos, resultado, estudo ou estatística. Faltou prova real:
  deixe de fora e pergunte ao aluno.
- `visual.produto`: o nome da pasta do entregável (Sistema 03) que tem `mockup.png`, pra ele
  aparecer na arte. Pra ver quais existem:
  `ls "<P>"/entregaveis/*/mockup.png` (o nome da pasta de cada um é o `visual.produto`). Sem mockup, o script avisa e segue sem produto (gere a capa/mockup no `/03-entregaveis`).

Mostre os anúncios ao aluno (headline da imagem, texto principal e título de cada um; hooks dos
vídeos) e ajuste até ele aprovar. Só depois siga.

## Passo 4 — Avisos da Meta

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/04-anuncios/scripts"; "$PY" "$S/anuncio_riscos.py" --pasta "<P>/anuncios"
```

O script só avisa (termina com 0 depois de ler os anúncios; 1 se não conseguir ler o
`anuncios.json`). Mostre os avisos. São só avisos: o aluno decide se muda (veja
`referencias/meta.md` pra sugerir versões mais seguras). Nunca reescreva sem ele pedir. Se ele
mudar algo, rode de novo pra conferir.

## Passo 5 — Montar as imagens

Cada anúncio estático vira duas imagens: 1:1 (feed) e 9:16 (Stories/Reels, com o texto e o
produto dentro das zonas seguras). A arte de fundo da KIE é opcional.

Com arte da KIE, **um anúncio por vez** (`--gerar-arte` exige `--id`; cada anúncio gera 2 cenas,
até ~150 s cada — rode o Bash com timeout de 10 minutos, `timeout: 600000` ms):

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/04-anuncios/scripts"; "$PY" "$S/anuncio_criativo.py" --projeto "<P>" --id '<id>' --gerar-arte
```

Sem `--id`, o script monta todos os estáticos de uma vez (sem gastar crédito). Sem `--paleta` ele
usa a do `pagina/config.json`; se a paleta for outra, acrescente `--paleta '<nome>'`:

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/04-anuncios/scripts"; "$PY" "$S/anuncio_criativo.py" --projeto "<P>" --paleta '<paleta>'
```

- Sem a chave da KIE, o `--gerar-arte` só mostra o prompt e onde salvar cada imagem
  (`<P>/anuncios/artes/arte-<id>-1x1.png` e `-9x16.png`); o aluno pode gerar em outra
  ferramenta, sem texto na imagem. Sem arte, o fundo sai com o degradê da paleta.
- Se a KIE falhar numa cena, o script avisa e segue montando; rode de novo com `--gerar-arte`
  depois, sem apagar nada: é seguro, ele só gera o que falta. Uma arte já salva em `artes/` nunca é
  regerada nem sobrescrita ("Reaproveitei a arte…"); apague o arquivo se quiser uma cena nova.
- Saída: `<P>/anuncios/criativos/<id>-1x1.jpg` e `<id>-9x16.jpg`.
- Olhe os JPEGs antes de mostrar ao aluno. Refaça o que ele pedir: mude o texto no
  `anuncios.json` e rode de novo SEM `--gerar-arte` (reaproveita a arte, não gasta crédito).
- Se aparecer "não achei o mockup", rode a capa no Sistema 03 (ou tire o `visual.produto`).

## Passo 6 — Exportar

```bash
PY="$HOME/.maquina/venv/bin/python"; S="$HOME/.claude/skills/04-anuncios/scripts"; "$PY" "$S/anuncio_exportar.py" --projeto "<P>"
```

Entregue ao aluno:

- `<P>/anuncios/textos.md` — o que colar em cada anúncio no Gerenciador (texto, título, botão, link).
- `<P>/anuncios/roteiros.md` — os vídeos pra gravar (um vídeo por hook, mesmo corpo); só existe se
  houver vídeos.
- `<P>/anuncios/plano-de-teste.xlsx` — uma linha por criativo/hook pra acompanhar o teste (se não
  der pra gerar o .xlsx, sai um `plano-de-teste.csv`).

Se o aluno mudar qualquer texto de anúncio depois de exportar, rode o exportar de novo (os
arquivos são refeitos). Linhas ⚠️ sobre imagens de anúncios que saíram do `anuncios.json` são só
aviso: nada é apagado, o aluno decide.

Se o script avisar que a página ainda não tem endereço, publique no Sistema 02 e rode o exportar
de novo pra preencher o link.

Explique o básico do teste: uma campanha, público aberto, todos os criativos juntos, orçamento
igual, esperar 3–4 dias antes de pausar os piores. Subir a campanha no Gerenciador é com o aluno.
