# skills/02-pagina-de-vendas/scripts/pagina_mockups.py
"""Gera os mockups da página em <P>/pagina/imagens/mockups/: topo (pack), um por bônus e as páginas do carrossel.

Uso: python pagina_mockups.py --projeto <P> [--estimar] [--sem-kie] [--refazer]
Com a chave da KIE, topo e bônus saem da KIE com fundo transparente; sem ela (ou se falhar), montados
por código. As páginas do carrossel são sempre montadas por código (fiéis ao material, e grátis).
"""
import argparse
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

_HOME = os.environ.get("MAQUINA_HOME") or os.path.expanduser("~/.maquina")
if _HOME not in sys.path:
    sys.path.append(_HOME)
try:
    from nucleo import kie
    from nucleo.chaves import obter_chave
    from nucleo.erros import registrar_log
    from nucleo.mockup import MAX_BONUS_PACK, gerar_capa_simples, gerar_mockup
    NUCLEO_OK = True
except Exception:  # noqa: BLE001
    NUCLEO_OK = False

from pagina_conteudo import PALETA_PADRAO, ler_config, normalizar  # noqa: E402
from pagina_render import fotos_da_pasta  # noqa: E402

MAX_PAGINAS = 6


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print("❌ Comando incompleto (falta --projeto). Use: pagina_mockups.py --projeto <pasta do projeto> "
              "[--estimar] [--sem-kie] [--refazer]", file=sys.stderr)
        raise SystemExit(1)


def _ler_conteudo(pagina: Path) -> dict:
    arq = pagina / "conteudo.json"
    try:
        bruto = json.loads(arq.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ValueError(f"Não achei {arq}. Escreva a copy (conteudo.json) antes dos mockups.") from err
    except (OSError, ValueError) as err:
        raise ValueError(f"O {arq} tem um erro de formatação JSON ({err}). Corrija e rode de novo.") from err
    return normalizar(bruto)[0]


def _capa(projeto: Path, slug: str) -> "Path | None":
    if not slug:
        return None
    capa = projeto / "entregaveis" / slug / "capa.png"
    return capa if capa.is_file() else None


def planejar(projeto: Path) -> dict:
    projeto = Path(projeto).resolve()
    pagina = projeto / "pagina"
    conteudo = _ler_conteudo(pagina)
    saida = pagina / "imagens" / "mockups"
    avisos = []
    hero = conteudo["hero"]
    principal = _capa(projeto, hero["entregavel"])
    if hero["entregavel"] and principal is None:
        avisos.append(f"topo: não achei entregaveis/{hero['entregavel']}/capa.png — usei uma capa simples "
                      "com o nome do produto (gere a capa no Sistema 03 pra ficar melhor).")
    nome = conteudo["rodape"]["nomeProduto"] or hero["headline"].replace("**", "")
    bonus = []
    if conteudo["bonus"]["ativo"]:
        for n, item in enumerate(conteudo["bonus"]["itens"], 1):
            capa = _capa(projeto, item["entregavel"])
            if item["entregavel"] and capa is None:
                avisos.append(f"bônus #{n}: não achei entregaveis/{item['entregavel']}/capa.png — usei uma capa simples.")
            bonus.append({"n": n, "titulo": item["titulo"], "capa": capa, "destino": saida / f"bonus-{n}.png"})
    paginas = (fotos_da_pasta(pagina / "imagens" / "carrossel")[:MAX_PAGINAS]
               if conteudo["carrossel"]["ativo"] else [])
    topo = {"ativo": hero["ativo"], "capa": principal, "nome": nome, "destino": saida / "topo.png"}
    return {"saida": saida, "topo": topo, "bonus": bonus, "paginas": paginas, "avisos": avisos,
            "kie": (1 if topo["ativo"] else 0) + len(bonus)}


def _capa_simples(pasta: Path, nome: str, titulo: str, rotulo: str, paleta_nome: str) -> Path:
    """Capa gerada a partir do título; o hash no nome reaproveita a mesma capa (e o cache do mockup)."""
    marca = hashlib.sha256(f"{titulo}|{rotulo}|{paleta_nome}".encode()).hexdigest()[:10]
    destino = pasta / f"{nome}-{marca}.png"
    for velha in pasta.glob(f"{nome}-*.png") if pasta.is_dir() else []:
        if velha != destino:
            velha.unlink()
    if not destino.exists():
        gerar_capa_simples(titulo, rotulo, destino, paleta_nome)
    return destino


def _limpar_sobras(saida: Path, n_bonus: int, n_paginas: int, com_topo: bool) -> None:
    for arq in saida.glob("bonus-*.png"):
        if not arq.stem.split("-")[1].isdigit() or int(arq.stem.split("-")[1]) > n_bonus:
            arq.unlink()
    for arq in saida.glob("pagina-*.png"):
        if not arq.stem.split("-")[1].isdigit() or int(arq.stem.split("-")[1]) > n_paginas:
            arq.unlink()
    if not com_topo and (saida / "topo.png").exists():
        (saida / "topo.png").unlink()


def gerar(plano: dict, paleta_nome: str, chave: "str | None", refazer: bool = False) -> dict:
    saida = plano["saida"]
    saida.mkdir(parents=True, exist_ok=True)
    capas = saida / ".capas"
    estado = {"chave": chave}
    modos, falhas = [], []

    def um(tipo, entradas, destino):
        r = gerar_mockup(tipo, entradas, destino, paleta_nome, estado["chave"], refazer)
        modos.append((destino.name, r["modo"]))
        if r["aviso"]:
            falhas.append(r["aviso"])
        if r["permanente"]:
            estado["chave"] = None  # sem crédito / chave recusada: repetir não adianta

    capas_bonus = [b["capa"] or _capa_simples(capas, f"bonus-{b['n']}", b["titulo"], f"Bônus #{b['n']}", paleta_nome)
                   for b in plano["bonus"]]
    if plano["topo"]["ativo"]:
        principal = plano["topo"]["capa"] or _capa_simples(capas, "principal", plano["topo"]["nome"], "Produto",
                                                           paleta_nome)
        um("pack", [principal] + capas_bonus[:MAX_BONUS_PACK], plano["topo"]["destino"])
    for b, capa in zip(plano["bonus"], capas_bonus):
        um("livro", [capa], b["destino"])
    for k, foto in enumerate(plano["paginas"], 1):
        um("pagina", [foto], saida / f"pagina-{k:02d}.png")
    _limpar_sobras(saida, len(plano["bonus"]), len(plano["paginas"]), plano["topo"]["ativo"])
    avisos = list(plano["avisos"])
    if falhas:
        avisos.append(f"⚠️ {len(falhas)} mockup(s) saíram no modo código porque a KIE falhou: {falhas[0]}")
    return {"modos": modos, "avisos": avisos}


def _estimativa(plano: dict, chave: "str | None") -> str:
    linhas = ["🖼️ Mockups desta página:"]
    if plano["topo"]["ativo"]:
        linhas.append(f"   • topo: pack do produto + {min(len(plano['bonus']), MAX_BONUS_PACK)} bônus")
    if plano["bonus"]:
        linhas.append(f"   • {len(plano['bonus'])} bônus (um mockup por bônus)")
    if plano["paginas"]:
        linhas.append(f"   • {len(plano['paginas'])} páginas do carrossel — montadas por código (grátis)")
    if not chave:
        linhas.append("💳 Sem a chave da KIE: tudo montado por código (grátis).")
    else:
        n = plano["kie"]
        try:
            saldo = f"Seu saldo: {kie.creditos(chave):g} créditos."
        except kie.KieErro as err:
            saldo = f"Não consegui ver o saldo ({err})."
        linhas.append(f"💳 Na KIE: até {n} gerações + {n} remoções de fundo (o que já foi gerado e não mudou "
                      f"não é cobrado de novo). {saldo}")
    return "\n".join(linhas)


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Gera os mockups da página de vendas.")
    ap.add_argument("--projeto", required=True)
    ap.add_argument("--estimar", action="store_true")
    ap.add_argument("--sem-kie", action="store_true")
    ap.add_argument("--refazer", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    if not NUCLEO_OK:
        print("❌ A Máquina não está instalada direito (não achei o núcleo). Rode o instalar.sh de novo.",
              file=sys.stderr)
        return 1
    projeto = Path(args.projeto).resolve()
    try:
        plano = planejar(projeto)
        chave = None if args.sem_kie else obter_chave("KIE_API_KEY")
        if args.estimar:
            print(_estimativa(plano, chave))
            return 0
        paleta_nome = ler_config(projeto / "pagina").get("paleta") or PALETA_PADRAO
        print("🎨 Gerando os mockups (com a KIE, 1–2 minutos por imagem)…")
        r = gerar(plano, paleta_nome, chave, args.refazer)
    except KeyboardInterrupt:
        print("Cancelado.", file=sys.stderr)
        return 130
    except ValueError as err:
        print(f"❌ {err}", file=sys.stderr)
        return 1
    except Exception as err:
        try:
            registrar_log(traceback.format_exc())
        except Exception:
            pass
        if "Executable doesn't exist" in str(err) or isinstance(err, ImportError):
            print("❌ O navegador que monta os mockups não está instalado. Rode o instalar.sh de novo.",
                  file=sys.stderr)
        else:
            print("❌ Algo deu errado ao gerar os mockups. Detalhes no log da Máquina (~/.maquina/log).",
                  file=sys.stderr)
        return 1
    for nome, modo in r["modos"]:
        rotulo = {"kie": "KIE", "codigo": "código", "cache": "já estava pronto"}[modo]
        print(f"   ✔ {nome} ({rotulo})")
    for aviso in r["avisos"]:
        print(aviso if aviso.startswith("⚠️") else f"⚠️ {aviso}")
    print(f"✅ Mockups em {plano['saida']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
