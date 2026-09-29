# Usando o núcleo dentro de uma skill

As skills chamam o núcleo sempre pelo comando `maquina` (via Bash), nunca importando arquivos soltos.

| Comando | Pra quê |
|---|---|
| `maquina projeto listar` | Ver os projetos do aluno; se houver mais de um, perguntar qual usar |
| `maquina projeto novo "<nome>"` | Criar pasta do projeto (imprime o caminho) |
| `maquina projeto caminho <slug>` | Caminho da pasta do projeto |
| `maquina oferta faltando <slug>` | Campos do oferta.md que faltam; se houver, entrevistar o aluno só sobre eles |
| `maquina status` | Quais chaves estão ativas (decide modo automático vs manual) |

Scripts Python próprios de uma skill rodam com `~/.maquina/venv/bin/python` e
`PYTHONPATH=~/.maquina`, podendo importar `nucleo.kie`, `nucleo.netlify`,
`nucleo.chaves.obter_chave` e `nucleo.projeto`.

Formato do `oferta.md`: frontmatter YAML com `nome, nicho, avatar, promessa, mecanismo,
preco, entregaveis[], bonus[], garantia, link_checkout, paleta` + corpo livre.
