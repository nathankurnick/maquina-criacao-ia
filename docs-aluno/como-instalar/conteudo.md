# Antes de começar

Este guia leva você, passo a passo, da pasta que acabou de baixar até o primeiro uso da Máquina Criação IA. Não precisa entender de programação. Basta seguir na ordem.

## O que você precisa ter

- Um Mac com macOS recente.
- Internet funcionando (o instalador baixa alguns programas).
- Cerca de 2 GB livres no disco.
- O **Claude Code** instalado e funcionando, com sua conta do Claude. Se ainda não tem, instale por aqui: [claude.com/claude-code](https://claude.com/claude-code).

> **Dica:** se você já consegue abrir o Terminal, digitar `claude` e conversar com ele, está tudo certo. Pode seguir pro próximo capítulo.

## Como abrir o Terminal

O Terminal é o programa do Mac onde você digita comandos. Aperte as teclas Command e Espaço, escreva **Terminal** e aperte Enter. Vai abrir uma janela com texto. É ali que a Máquina trabalha.

# Instalando o Python

O Python é o programa que faz a Máquina funcionar por baixo dos panos. O instalador da Máquina procura por ele sozinho e avisa se precisar. Você só precisa seguir esta parte **se o instalador disser** que falta o Python 3.10 ou mais novo.

## Passo 1: instalar o Homebrew

O Homebrew é uma loja de programas para o Mac. Acesse [brew.sh](https://brew.sh), copie o comando que aparece na página, cole no Terminal e aperte Enter.

> **Atenção:** o Homebrew vai pedir a senha do seu Mac. Ao digitar, nada aparece na tela (nem bolinhas). É normal. Digite a senha e aperte Enter.

> **Atenção:** antes do Homebrew, o Mac pode instalar as Ferramentas de Linha de Comando (Xcode Command Line Tools). Vai aparecer uma janela pedindo para instalar: aceite. Pode levar de 10 a 30 minutos. É normal demorar.

## Passo 2: instalar o Python

Quando o Homebrew terminar, ele mostra no final umas linhas chamadas "Next steps". Rode essas linhas (no Mac com chip Apple, é `eval "$(/opt/homebrew/bin/brew shellenv)"`) ou, mais simples, feche o Terminal e abra um novo. Depois cole este comando e aperte Enter:

`brew install python@3.12`

Espere terminar (alguns minutos). Quando o cursor voltar a piscar, o Python está instalado.

# Rodando o instalador

## Abrindo o instalador

1. Descompacte o zip que você baixou (dois cliques no arquivo `.zip`). Vai aparecer uma pasta.
2. Abra a pasta e dê dois cliques em **Instalar Máquina.command**.
3. Vai abrir uma janela do Terminal e a instalação começa.

> **Atenção:** na primeira vez, o Mac pode bloquear o arquivo dizendo que não conseguiu verificar o desenvolvedor. Não é vírus. Faça assim:

- **macOS 15 (Sequoia) ou mais novo:** dê dois cliques, feche o aviso ("A Apple não pôde verificar..."), abra **Ajustes do Sistema**, entre em **Privacidade e Segurança**, role até o fim e clique em **Abrir Mesmo Assim** ao lado de "Instalar Máquina.command". Confirme com a senha do Mac.
- **macOS mais antigo:** clique com o **botão direito** no arquivo, escolha **Abrir** e, na janela que aparecer, clique em **Abrir** de novo.

## O que aparece na janela

O instalador mostra o que está fazendo, uma etapa por vez:

- A versão da Máquina que você está instalando.
- Instalando dependências: baixa os programas de apoio. Pode levar alguns minutos.
- Baixando o navegador usado na pesquisa de ofertas: é um arquivo grande, então tenha paciência.
- Uma lista com os cinco sistemas instalados.

Não feche a janela enquanto isso acontece. No fim, aparece a mensagem **Máquina Criação IA instalada!**

# As chaves (opcionais)

Depois de instalar, o instalador pergunta pelas chaves. Chave é uma espécie de senha que liga a Máquina a um serviço externo. **Nenhuma é obrigatória.** Você pode apertar Enter para pular e configurar mais tarde.

## Chave do KIE (imagens)

Serve para criar imagens: capas dos seus produtos, mockups e criativos de anúncio. Você pega a chave em [kie.ai/api-key](https://kie.ai/api-key). Sem ela, a Máquina continua funcionando, mas as imagens precisam ser feitas por você e colocadas na pasta do projeto.

## Chave do Netlify (publicar páginas)

Serve para colocar suas páginas de vendas no ar com um só comando. Você pega a chave em [app.netlify.com/user/applications](https://app.netlify.com/user/applications#personal-access-tokens), na parte de tokens de acesso pessoal. Sem ela, a Máquina entrega a página pronta e você publica onde preferir.

> **Dica:** para colocar ou trocar uma chave depois, abra o Terminal e digite `maquina chaves`. A Máquina pergunta uma por uma.

# Primeiro uso

Chegou a hora de testar.

## Abrindo a Máquina

- [ ] Feche o Terminal que você usou na instalação
- [ ] Abra um Terminal novo
- [ ] Digite `claude` e aperte Enter
- [ ] Digite `/01-pesquisa-ofertas` e aperte Enter

Se o Claude começar a conversar com você sobre o seu nicho, a instalação deu certo.

## Os cinco sistemas

Use na ordem. Cada um entrega uma peça do seu negócio:

1. `/01-pesquisa-ofertas`: pesquisa o mercado e ajuda a escolher a oferta.
2. `/02-pagina-de-vendas`: cria a página de vendas da oferta.
3. `/03-entregaveis`: cria o produto que você entrega (ebook, guia, planilha, aulas).
4. `/04-anuncios`: cria os anúncios para atrair gente pra página.
5. `/05-funil`: monta o resto do funil (upsell, downsell e página de obrigado).

## Onde ficam os seus projetos

Tudo o que você cria fica na pasta **MaquinaIA**, dentro da sua pasta de usuário. Cada oferta tem a sua subpasta. Você pode abrir, copiar e guardar esses arquivos como qualquer outro.

# Como atualizar

Quando sair uma versão nova, você fica sabendo na área de membros do curso.

1. Baixe o zip novo na área de membros.
2. Descompacte (dois cliques no arquivo `.zip`).
3. Dê dois cliques em **Instalar Máquina.command**, do mesmo jeito da primeira vez.

Suas chaves e seus projetos continuam onde estão. Depois de atualizar, feche e abra o Claude de novo.

> **Dica:** para saber qual versão você tem, abra o Terminal e digite `maquina atualizar`. Ele mostra a versão instalada e repete esses passos.

# Resolvendo problemas

Se algo der errado, procure a mensagem na tabela. Na maioria das vezes, rodar o instalador de novo resolve.

| O que apareceu | O que fazer |
|---|---|
| Não achei o Claude Code | Instale o Claude Code em [claude.com/claude-code](https://claude.com/claude-code), abra ele uma vez para entrar na sua conta e rode o instalador de novo. |
| Precisa do Python 3.10 ou mais novo | Siga o capítulo "Instalando o Python" e depois rode o instalador de novo. |
| Falhou ao baixar o navegador | Quase sempre é a internet. Confira a conexão e rode o instalador de novo. |
| maquina: command not found | Feche o Terminal e abra um novo. Se continuar, digite `~/.local/bin/maquina` no lugar de `maquina`. |
| A Máquina não está instalada direito | Rode o instalador de novo (dois cliques em Instalar Máquina.command). |
| Chave recusada | Confira se copiou a chave inteira, sem espaço no começo ou no fim. Depois digite `maquina chaves` e cole de novo. |
| O Mac não deixa abrir o instalador | macOS 15 (Sequoia) ou mais novo: feche o aviso, vá em Ajustes do Sistema, Privacidade e Segurança, role até o fim e clique em **Abrir Mesmo Assim**. macOS mais antigo: botão direito no arquivo, **Abrir**, e **Abrir** de novo. |
| brew: command not found | Feche o Terminal e abra um novo. Se continuar, rode as linhas "Next steps" que o Homebrew mostrou no final da instalação (no Mac com chip Apple: `eval "$(/opt/homebrew/bin/brew shellenv)"`) e tente de novo. |

## Pedindo ajuda ao suporte

Se nada resolver, mande ao suporte um print da janela do Terminal e os arquivos de registro técnico: se a falha foi durante a instalação, `~/.maquina/log/instalacao.log`; se foi em outro momento, `~/.maquina/log/maquina.log`. Com essas duas coisas fica muito mais rápido descobrir o problema.
