# Máquina Criação IA

5 sistemas de IA que rodam dentro do Claude Code: **/01-pesquisa-ofertas**, **/02-pagina-de-vendas**,
**/03-entregaveis**, **/04-anuncios** e **/05-funil**.

## Como instalar (aluno)

Abra o Claude Code no Terminal (`claude`) e mande esta mensagem:

```
Instala a Máquina Criação IA pra mim: https://github.com/nathankurnick/maquina-criacao-ia
```

O Claude faz a instalação e te ajuda nos passos que dependem de você, como a senha do Mac e as chaves de API.

> **Claude Code:** siga [INSTALAR-COM-CLAUDE.md](INSTALAR-COM-CLAUDE.md) passo a passo.
> Versão em texto puro: https://raw.githubusercontent.com/nathankurnick/maquina-criacao-ia/main/INSTALAR-COM-CLAUDE.md

Prefere fazer sem o Claude? Baixe o zip na área de membros e dê dois cliques em `Instalar Máquina.command`.

## Desenvolvimento

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest            # testes
bash dev/empacotar.sh       # gera dist/maquina-criacao-ia-<versão>.zip
bash dev/testar_pacote.sh   # instala o zip num HOME limpo e roda os 5 sistemas
```
