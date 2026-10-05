# skills/02-pagina-de-vendas/scripts/pagina_mockups.py
"""Gera os mockups da página em <P>/pagina/imagens/mockups/: topo (pack), um por bônus, as páginas do carrossel
e as fotos dos cartões de "O que você vai encontrar" que têm "arte" (só com a KIE).

Uso: python pagina_mockups.py --projeto <P> [--pagina <pasta da página>] [--estimar] [--sem-kie] [--refazer]
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

from pagina_conteudo import PALETA_PADRAO, PALETAS, normalizar  # noqa: E402
from pagina_render import fotos_da_pasta  # noqa: E402

MAX_PAGINAS = 6


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print("❌ Comando incompleto (falta --projeto). Use: pagina_mockups.py --projeto <pasta do projeto> "
              "[--pagina <pasta>] [--estimar] [--sem-kie] [--refazer]", file=sys.stderr)
        raise SystemExit(1)


def _ler_conteudo(pagina: Path) -> "tuple[dict, list[str]]":
    arq = pagina / "conteudo.json"
    try:
        bruto = json.loads(arq.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ValueError(f"Não achei {arq}. Escreva a copy (conteudo.json) antes dos mockups.") from err
    except (OSError, ValueError) as err:
        raise ValueError(f"O {arq} tem um erro de formatação JSON ({err}). Corrija e rode de novo.") from err
    conteudo, avisos = normalizar(bruto)
    return conteudo, [a for a in avisos if "entregavel" in a]


def _capa(projeto: Path, slug: str) -> "Path | None":
    if not slug:
        return None
    capa = projeto / "entregaveis" / slug / "capa.png"
    return capa if capa.is_file() else None


def _paleta_efetiva(projeto: Path, pagina: Path) -> str:
    """config.json da página > paleta do oferta.md > padrão (mesma cadeia do funil_oto)."""
    try:
        dados = json.loads((pagina / "config.json").read_text(encoding="utf-8"))
        nome = dados.get("paleta", "") if isinstance(dados, dict) else ""
        if nome in PALETAS:
            return nome
    except (OSError, ValueError):
        pass
    try:
        from nucleo.projeto import ler_oferta
        o = ler_oferta(projeto)
        nome = getattr(o, "paleta", "") if o else ""
        if nome in PALETAS:
            return nome
    except Exception:  # noqa: BLE001
        pass
    return PALETA_PADRAO


def planejar(projeto: Path, pagina: "Path | None" = None) -> dict:
    projeto = Path(projeto).resolve()
    pagina = Path(pagina).resolve() if pagina else projeto / "pagina"
    conteudo, avisos = _ler_conteudo(pagina)
    saida = pagina / "imagens" / "mockups"
    hero = conteudo["hero"]
    principal = _capa(projeto, hero["entregavel"])
    if hero["ativo"] and hero["entregavel"] and principal is None:
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
    cards = []
    if conteudo["conteudo"]["ativo"]:
        for n, item in enumerate(conteudo["conteudo"]["itens"], 1):
            propria = item["imagem"] and (pagina / "imagens" / "conteudo" / item["imagem"]).is_file()
            if item["arte"] and not propria:
                cards.append({"n": n, "arte": item["arte"], "destino": saida / f"conteudo-{n}.png"})
    return {"saida": saida, "topo": topo, "bonus": bonus, "paginas": paginas, "cards": cards, "avisos": avisos,
            "kie": (1 if topo["ativo"] else 0) + len(bonus)}


PROMPT_CARD = ("{arte}. Photorealistic, natural light, sharp focus, 4:3 landscape composition. "
               "No text, no letters, no numbers, no logos, no watermarks.")


def _gerar_cards(cards: list, chave: "str | None", refazer: bool) -> "tuple[list, list[str]]":
    """Foto de cada cartão pela KIE. Sem chave, o cartão fica só com o ícone (não há versão por código)."""
    modos, falhas = [], []
    for c in cards:
        destino = c["destino"]
        marca = hashlib.sha256(PROMPT_CARD.format(arte=c["arte"]).encode()).hexdigest()
        selo = destino.with_name(f".{destino.stem}.arte")
        if not refazer and destino.exists() and selo.is_file() and selo.read_text(encoding="utf-8") == marca:
            modos.append((destino.name, "cache"))
            continue
        if not chave:
            falhas.append(f"cartão {c['n']}: sem a chave da KIE a foto não é gerada (fica só o ícone). "
                          "Coloque uma foto em imagens/conteudo/ e o nome dela em \"imagem\".")
            continue
        try:
            kie.gerar_imagem(chave, PROMPT_CARD.format(arte=c["arte"]), "4:3", destino)
            selo.write_text(marca, encoding="utf-8")
            modos.append((destino.name, "kie"))
        except kie.KieErroPermanente as err:
            falhas.append(f"cartão {c['n']}: {err}")
            chave = None
        except kie.KieErro as err:
            falhas.append(f"cartão {c['n']}: {err}")
    return modos, falhas


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


def _limpar_sobras(saida: Path, n_bonus: int, n_paginas: int, com_topo: bool, cards: "set[int] | None" = None) -> None:
    for arq in saida.glob("conteudo-*.png"):
        n = arq.stem.split("-")[1]
        if not n.isdigit() or int(n) not in (cards or set()):
            arq.unlink()
            arq.with_name(f".{arq.stem}.arte").unlink(missing_ok=True)
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
    contagem = {"codigo": 0}

    def um(tipo, entradas, destino):
        # páginas do carrossel nunca usam a KIE (fiéis ao material, e grátis)
        usa_chave = estado["chave"] if tipo != "pagina" else None
        r = gerar_mockup(tipo, entradas, destino, paleta_nome, usa_chave, refazer)
        modos.append((destino.name, r["modo"]))
        if tipo != "pagina" and chave is not None and r["modo"] == "codigo":
            contagem["codigo"] += 1
        if r["aviso"]:
            falhas.append(r["aviso"])
        if r["permanente"]:
            estado["chave"] = None  # sem crédito / chave recusada: repetir não adianta

    capas_bonus = [b["capa"] or _capa_simples(capas, f"bonus-{b['n']}", b["titulo"], f"Bônus #{b['n']}", paleta_nome)
                   for b in plano["bonus"]]
    principal_usada = None
    if plano["topo"]["ativo"]:
        principal = principal_usada = plano["topo"]["capa"] or _capa_simples(capas, "principal", plano["topo"]["nome"], "Produto",
                                                           paleta_nome)
        um("pack", [principal] + capas_bonus[:MAX_BONUS_PACK], plano["topo"]["destino"])
    for b, capa in zip(plano["bonus"], capas_bonus):
        um("livro", [capa], b["destino"])
    for k, foto in enumerate(plano["paginas"], 1):
        um("pagina", [foto], saida / f"pagina-{k:02d}.png")
    modos_cards, falhas_cards = _gerar_cards(plano.get("cards", []), estado["chave"], refazer)
    modos.extend(modos_cards)
    _limpar_sobras(saida, len(plano["bonus"]), len(plano["paginas"]), plano["topo"]["ativo"],
                   {c["n"] for c in plano.get("cards", [])})
    if capas.is_dir():
        em_uso = {c.resolve() for c in capas_bonus + [principal_usada] if c is not None}
        for velha in capas.glob("*.png"):
            if velha.resolve() not in em_uso:
                velha.unlink()
    avisos = list(falhas_cards)
    if contagem["codigo"] and falhas:
        avisos.append(f"⚠️ {contagem['codigo']} mockup(s) saíram no modo código porque a KIE falhou: {falhas[0]}")
    return {"modos": modos, "avisos": avisos}


def _estimativa(plano: dict, chave: "str | None") -> str:
    linhas = ["🖼️ Mockups desta página:"]
    if plano["topo"]["ativo"]:
        linhas.append(f"   • topo: pack do produto + {min(len(plano['bonus']), MAX_BONUS_PACK)} bônus")
    if plano["bonus"]:
        linhas.append(f"   • {len(plano['bonus'])} bônus (um mockup por bônus)")
    if plano["paginas"]:
        linhas.append(f"   • {len(plano['paginas'])} páginas do carrossel — montadas por código (grátis)")
    if plano.get("cards"):
        linhas.append(f"   • {len(plano['cards'])} fotos dos cartões de conteúdo (só com a KIE)")
    if not chave:
        linhas.append("💳 Sem a chave da KIE: tudo montado por código (grátis).")
    else:
        n = plano["kie"]
        fotos = len(plano.get("cards", []))
        try:
            saldo = f"Seu saldo: {kie.creditos(chave):g} créditos."
        except Exception as err:  # noqa: BLE001 - o saldo é só informativo
            try:
                registrar_log(traceback.format_exc())
            except Exception:  # noqa: BLE001
                pass
            saldo = "Não consegui ver o saldo agora." if not isinstance(err, kie.KieErro) else \
                f"Não consegui ver o saldo ({err})."
        extra = f" + {fotos} fotos de cartão" if fotos else ""
        linhas.append(f"💳 Na KIE: até {n} gerações + {n} remoções de fundo{extra} (o que já foi gerado e não mudou "
                      f"não é cobrado de novo). {saldo}")
    return "\n".join(linhas)


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Gera os mockups da página de vendas.")
    ap.add_argument("--projeto", required=True)
    ap.add_argument("--pagina", default="")
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
        pagina = Path(args.pagina).resolve() if args.pagina else projeto / "pagina"
        plano = planejar(projeto, pagina)
        chave = None if args.sem_kie else obter_chave("KIE_API_KEY")
        print(_estimativa(plano, chave))
        for aviso in plano["avisos"]:
            print(f"⚠️ {aviso}")
        if args.estimar:
            return 0
        paleta_nome = _paleta_efetiva(projeto, pagina)
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
