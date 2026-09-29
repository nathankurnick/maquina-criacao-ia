# Usando o núcleo dentro de uma skill

As skills chamam o núcleo sempre pelo comando `maquina` (via Bash), nunca importando arquivos soltos.

| Comando | Pra quê |
|---|---|
| `maquina projeto listar` | Ver os projetos do aluno; se houver mais de um, perguntar qual usar |
| `maquina projeto novo "<nome>"` | Criar pasta do projeto (imprime o caminho) |
| `maquina projeto caminho <slug>` | Caminho da pasta do projeto |
| `maquina oferta faltando <slug>` | Campos do oferta.md que faltam; se houver, entrevistar o aluno só sobre eles |
| `maquina oferta mostrar <slug>` | Imprime a oferta inteira como JSON (todos os campos, incluindo `corpo`); leia por aqui |
| `maquina oferta definir <slug> campo=valor [campo=valor ...]` | Grava campos simples (`nome, nicho, avatar, promessa, mecanismo, preco, garantia, link_checkout, paleta`); cria o oferta.md se não existir; divide só no primeiro `=` |
| `maquina oferta adicionar <slug> <entregaveis\|bonus> "<item>"` | Acrescenta um item numa lista (sem duplicar) |
| `maquina status` | Quais chaves estão ativas (decide modo automático vs manual) |
| `maquina status --json` | Igual, em JSON: `{"versao", "chaves": {"KIE_API_KEY": true/false, "NETLIFY_TOKEN": true/false}, "projetos": [...]}` |

Scripts Python próprios de uma skill rodam com `~/.maquina/venv/bin/python` e
`PYTHONPATH=~/.maquina`, podendo importar `nucleo.kie`, `nucleo.netlify`,
`nucleo.chaves.obter_chave` e `nucleo.projeto`.

Formato do `oferta.md`: frontmatter YAML com `nome, nicho, avatar, promessa, mecanismo,
preco, entregaveis[], bonus[], garantia, link_checkout, paleta` + corpo livre.

## Regras para as skills

- **Nunca escreva o YAML do `oferta.md` à mão.** Leia com `maquina oferta mostrar` e grave
  com `maquina oferta definir` / `maquina oferta adicionar`: o núcleo cuida das aspas e
  preserva o corpo e as listas.
- Se o comando `maquina` não for encontrado (o PATH ainda não foi recarregado), chame
  `"$HOME/.local/bin/maquina"`.
- Tarefas longas na KIE (`aguardar` pode levar minutos) devem rodar em segundo plano ou com
  um timeout explícito no Bash, e salvar o resultado de cada item assim que ele terminar
  (não só no fim do lote).
- `KieErroPermanente` significa que repetir não adianta (chave, pedido ou tarefa recusados);
  qualquer outro `KieErro` é transitório. `NetlifySiteNaoExiste` significa que o site foi
  apagado: crie um novo (`publicar_pasta` sem `site_id`).
- A publicação na Netlify envia só arquivos web (html, css, js, imagens, fontes, vídeos, pdf);
  `conteudo.json` e arquivos ocultos nunca vão.
