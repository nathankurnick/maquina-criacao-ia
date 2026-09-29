# Instalação guiada pelo Claude Code

Este arquivo é pra você, Claude Code. Um aluno da Máquina Criação IA te mandou o link deste repositório
(ou a pasta do zip) e quer instalar. Siga os passos na ordem. Fale com o aluno em português simples:
ele não é programador. Antes de cada passo, diga em uma frase o que vai fazer. Não despeje logs nem
jargão técnico nele.

## Regras

- **Chave de API nunca vem pelo chat.** Se o aluno colar uma chave aqui, não use. Explique que a chave
  vai direto no Terminal com `maquina chaves` (passo 6) e sugira que ele gere uma nova, já que essa
  ficou no histórico da conversa.
- **Senha do Mac é sempre o aluno quem digita**, no Terminal dele (Homebrew). Você não consegue e não deve.
- **Só macOS.** Se `uname` não retornar `Darwin`, avise que a Máquina por enquanto só roda no Mac e pare.
- O instalador pode rodar de novo quantas vezes precisar. Chaves (`~/.maquina/chaves.env`) e projetos
  (`~/MaquinaIA`) são preservados. Se algo falhar no meio, corrija e rode de novo.

## 1. Conferir o Mac

```bash
uname -s; sw_vers -productVersion; uname -m
```

## 2. Python 3.10 ou mais novo (do Homebrew)

O instalador **não aceita** o `/usr/bin/python3` da Apple: num Mac sem as ferramentas do Xcode ele
abre um popup de instalação. Procure um Python bom:

```bash
for p in /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.10 /usr/local/bin/python3.13 /usr/local/bin/python3.12 /usr/local/bin/python3.11 /usr/local/bin/python3.10; do [ -x "$p" ] && echo "OK $p" && break; done; ls /opt/homebrew/bin/brew /usr/local/bin/brew 2>/dev/null
```

- Apareceu `OK ...`? Pule pro passo 3.
- Tem `brew` mas não tem Python? Rode `brew install python@3.12` (use `/opt/homebrew/bin/brew` ou
  `/usr/local/bin/brew` com o caminho completo se `brew` não estiver no PATH).
- Não tem `brew`? O aluno instala o Homebrew **no Terminal dele** (pede a senha do Mac). Passe exatamente isto:
  1. Abrir o app **Terminal** (Cmd+Espaço, digitar "Terminal", Enter).
  2. Colar e dar Enter:
     `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
  3. Digitar a senha do Mac quando pedir (não aparece nada enquanto digita, é normal) e apertar Enter
     quando pedir confirmação. Se aparecer aviso das ferramentas do Xcode, clicar em Instalar e esperar.
  4. No fim, o Homebrew mostra "Next steps" com dois comandos. Colar os dois. Num Mac com chip Apple são:
     `echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile` e `eval "$(/opt/homebrew/bin/brew shellenv)"`
  5. Te avisar quando terminar.

  Quando ele avisar, rode `brew install python@3.12` pelo caminho completo e repita a checagem.

## 3. Pegar os arquivos da Máquina

**Se o aluno já tem a pasta do zip** (área de membros), use essa pasta. Procure em `~/Downloads`
uma pasta `maquina-criacao-ia-*` com `instalar.sh` dentro. Se só tiver o `.zip`, descompacte com
`ditto -x -k <zip> ~/Downloads`. O `unzip` estraga o nome com acento.

**Se veio pelo link do GitHub**, baixe sem `git`. O `git` pode disparar o popup do Xcode:

```bash
rm -rf ~/.maquina-fonte && mkdir -p ~/.maquina-fonte && curl -fsSL https://github.com/nathankurnick/maquina-criacao-ia/archive/refs/heads/main.tar.gz | tar -xz -C ~/.maquina-fonte --strip-components=1 && ls ~/.maquina-fonte/instalar.sh
```

Se der erro 404, o link não está liberado pra ele. Peça que baixe o zip na área de membros e volte
pra este passo com a pasta do zip.

## 4. Rodar o instalador

Use a pasta do passo 3 no lugar de `<PASTA>`. Leva de 2 a 5 minutos, porque baixa as dependências e
o navegador da pesquisa. Rode com timeout longo (10 min):

```bash
bash "<PASTA>/instalar.sh" --sem-chaves
```

Se falhar, a mensagem em português diz o motivo. Os detalhes técnicos ficam em
`~/.maquina/log/instalacao.log` (leia com `tail -40`). Causas comuns:
- **Sem internet ou rede instável:** rode de novo.
- **"Não achei o Claude Code":** o comando `claude` não está no PATH do shell. Descubra onde está
  (`ls ~/.local/bin/claude ~/.claude/local/claude /opt/homebrew/bin/claude 2>/dev/null`) e rode de novo
  com `PATH="<pasta do claude>:$PATH"` na frente.
- **Python:** volte pro passo 2.

## 5. Conferir

```bash
~/.local/bin/maquina status
```

Deve mostrar a versão e as 5 skills. As chaves ainda aparecem como não configuradas, e isso é esperado.

## 6. Chaves de API (opcionais)

São duas, e as duas são opcionais. Sem elas, o recurso funciona no modo manual.
- **KIE** (https://kie.ai/api-key): gera imagens de anúncios, capas e mockups. É paga por uso.
- **Netlify** (https://app.netlify.com/user/applications#personal-access-tokens): publica as páginas
  sozinho. É grátis. Sem ela, o aluno arrasta a pasta pro Netlify Drop.

O comando é interativo e não roda por aqui. Peça ao aluno para abrir o Terminal e rodar:

```
maquina chaves
```

Se aparecer "command not found", ele precisa fechar e abrir o Terminal de novo (ou usar
`~/.local/bin/maquina chaves`). Cada chave é testada na hora. Enter pula.

## 7. Recarregar o Claude Code

As skills novas só aparecem numa sessão nova. Peça ao aluno para digitar `/exit`, abrir o Terminal
de novo, rodar `claude` e digitar `/01`. Os 5 sistemas devem aparecer.

## 8. Explicar como usar

Termine com um resumo curto:

- Os sistemas funcionam em sequência, e tudo de um produto fica em `~/MaquinaIA/<nome-do-projeto>/`:
  1. **/01-pesquisa-ofertas**: acha ofertas validadas no nicho e escolhe uma pra modelar.
  2. **/02-pagina-de-vendas**: escreve e monta a página de vendas e publica na Netlify.
  3. **/03-entregaveis**: cria o produto (ebook em PDF, planilhas, capa e mockup).
  4. **/04-anuncios**: cria os criativos, os textos, os roteiros de vídeo e o plano de teste.
  5. **/05-funil**: monta upsell e downsell e desenha o mapa do funil.
- Dá pra começar em qualquer sistema. Sem o 01, a Máquina pergunta o que precisa.
- Na dúvida, rodar `maquina status`.
- **Atualizar:** mandar o link (ou o zip novo) pro Claude Code de novo e pedir para atualizar. É este
  mesmo passo a passo, e as chaves e os projetos continuam onde estão.

Pergunte se ele quer começar agora pelo `/01-pesquisa-ofertas`. Lembre que é numa sessão nova do Claude.
