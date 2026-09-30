# skills/05-funil/scripts/funil_mapa.py
"""Desenha o mapa do funil (PNG + HTML) com a projeção de ticket médio calculada em código.

Uso: python funil_mapa.py --projeto <P> [--paleta nome]
"""
import argparse
import html
import json
import os
import sys
import traceback
from pathlib import Path

_HOME = os.environ.get("MAQUINA_HOME") or os.path.expanduser("~/.maquina")
if _HOME not in sys.path:
    sys.path.append(_HOME)
try:
    from nucleo.erros import registrar_log
    from nucleo.paletas import PALETA_PADRAO, PALETAS, paleta
    NUCLEO_OK = True
except Exception:  # noqa: BLE001
    NUCLEO_OK = False

from funil_dados import META_AUMENTO, REFERENCIAS, brl, ler_funil, projetar  # noqa: E402

CSS = Path(__file__).resolve().parent.parent / "template" / "mapa.css"
ROTULO = {"bump": "Order bump", "upsell": "Upsell", "downsell": "Downsell"}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print("❌ Comando incompleto (falta --projeto ou valor inválido). Use: funil_mapa.py --projeto <P> "
              "[--paleta nome]", file=sys.stderr)
        raise SystemExit(1)


def e(t) -> str:
    return html.escape(str(t), quote=True)


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%".replace(".", ",") if 0 < v < 0.01 else f"{v * 100:.0f}%"


def _caixa_oferta(etapa: str, d: dict, rotulo: str = "") -> str:
    baixo, alto = REFERENCIAS[etapa]
    fora = (' <strong class="fora">⚠️ fora da referência</strong>'
            if not baixo - 1e-9 <= d["conversao"] <= alto + 1e-9 else "")
    return (f'<div class="caixa oferta"><p class="etapa">{e(rotulo or ROTULO[etapa])}</p><p class="nome">{e(d["nome"])}</p>'
            f'<p class="preco">{brl(d["preco"])}</p><p class="conv">Conversão usada: {_pct(d["conversao"])} '
            f'(referência: {baixo * 100:.0f}–{alto * 100:.0f}%){fora}</p></div>')


def _caixa(etapa: str, texto: str, extra: str = "") -> str:
    return f'<div class="caixa"><p class="etapa">{e(etapa)}</p><p class="nome">{e(texto)}</p>{extra}</div>'


def _seta(texto: str = "") -> str:
    return f'<div class="seta">↓{f"<small>{e(texto)}</small>" if texto else ""}</div>'


def html_mapa(funil: dict, projecao: dict, paleta_nome: str) -> str:
    cores = paleta(paleta_nome)
    variaveis = ":root{" + ";".join(f"--pg-{k}:{v}" for k, v in cores.items()) + "}"
    front = funil["front"]
    partes = [_caixa("Anúncio", "Meta Ads (Sistema 04)"), _seta(),
              _caixa("Página de vendas", front["nome"], f'<p class="preco">{brl(front["preco"])}</p>'), _seta()]
    checkout = _caixa("Checkout", "Produto principal", f'<p class="preco">{brl(front["preco"])}</p>')
    partes.append(f'<div class="linha">{checkout}</div>')
    bumps = funil.get("bumps") or []
    if bumps:
        caixas = "".join(_caixa_oferta("bump", b, f"Order bump {n}") for n, b in enumerate(bumps, 1))
        partes += [_seta("no mesmo checkout"), f'<div class="linha bumps">{caixas}</div>']
    if funil.get("upsell"):
        partes += [_seta("comprou"), f'<div class="linha">{_caixa_oferta("upsell", funil["upsell"])}</div>']
        if funil.get("downsell"):
            partes += [_seta("recusou o upsell"), f'<div class="linha">{_caixa_oferta("downsell", funil["downsell"])}</div>']
    partes += [_seta(), _caixa("Obrigado", "Área de membros", '<p class="conv">Boas-vindas e acesso (mensagens.md)</p>')]
    aumento = projecao["aumento_upsell_pct"]
    sem_upsell = not funil.get("upsell")
    if sem_upsell:
        selo, fim = "", ""
    elif aumento < META_AUMENTO[0]:
        selo, fim = "⚠️ abaixo da meta", ""
    elif aumento <= META_AUMENTO[1]:
        selo, fim = "✅ dentro da meta", ""
    else:
        selo, fim = "✅ acima da meta", " — confira se as conversões não estão otimistas"
    linha_up = (f"Sem upsell ainda — a meta de {META_AUMENTO[0]:.0f}–{META_AUMENTO[1]:.0f}% é do upsell." if sem_upsell
                else f"Aumento do upsell: {aumento:.0f}% — {selo} de {META_AUMENTO[0]:.0f}–{META_AUMENTO[1]:.0f}%{fim}")
    resumo = (f'<div class="resumo"><p class="grande">Ticket médio projetado (produto + {len(bumps)} bumps + upsell + downsell): '
              f'<span>{brl(projecao["ticket_medio"])}</span></p>'
              f'<p>Aumento total sobre o produto principal: {projecao["aumento_pct"]:.0f}%</p>'
              f'<p>{linha_up}</p>'
              '<p class="nota">A meta vale só para o upsell (conversão × ticket do upsell ÷ produto principal). '
              'Conversões são números de referência — troque pelos seus quando tiver dados.</p></div>')
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Mapa do funil</title>'
            f"<style>{variaveis}\n{CSS.read_text(encoding='utf-8')}</style></head><body><div class=\"mapa\">"
            f'<h1>Mapa do funil</h1><p class="sub">{e(front["nome"])}</p>{"".join(partes)}{resumo}</div></body></html>')


def _paleta_config(pasta_projeto: Path) -> str:
    try:
        dados = json.loads((pasta_projeto / "pagina" / "config.json").read_text(encoding="utf-8"))
        return dados.get("paleta", "") if isinstance(dados, dict) else ""
    except (OSError, ValueError):
        return ""


def _paleta_oferta(pasta_projeto: Path) -> str:
    try:
        from nucleo.projeto import ler_oferta
        o = ler_oferta(pasta_projeto)
        n = getattr(o, "paleta", "") if o else ""
        return n if n in PALETAS else ""
    except Exception:  # noqa: BLE001
        return ""


def gerar(pasta_projeto: Path, paleta_nome: str = "") -> dict:
    from playwright.sync_api import sync_playwright

    pasta_projeto = Path(pasta_projeto).resolve()
    pasta = pasta_projeto / "funil"
    funil = ler_funil(pasta)
    projecao = projetar(funil)
    nome = paleta_nome or _paleta_config(pasta_projeto) or _paleta_oferta(pasta_projeto) or PALETA_PADRAO
    documento = html_mapa(funil, projecao, nome)
    html_arq, png_arq = pasta / "mapa.html", pasta / "mapa.png"
    tmp_html, tmp_png = pasta / ".mapa.html", pasta / ".mapa.png"
    try:
        tmp_html.write_text(documento, encoding="utf-8")
        with sync_playwright() as p:
            nav = p.chromium.launch()
            try:
                pg = nav.new_page(viewport={"width": 1080, "height": 800})
                pg.goto(tmp_html.as_uri(), wait_until="load")
                pg.screenshot(path=str(tmp_png), full_page=True)
            finally:
                try:
                    nav.close()
                except Exception:
                    pass
        os.replace(tmp_png, png_arq)
        os.replace(tmp_html, html_arq)
    finally:
        tmp_html.unlink(missing_ok=True)
        tmp_png.unlink(missing_ok=True)
    return {"png": png_arq, "html": html_arq, "projecao": projecao}


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Desenha o mapa do funil.")
    ap.add_argument("--projeto", required=True)
    ap.add_argument("--paleta", default="")
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    if not NUCLEO_OK:
        print("❌ A Máquina não está instalada direito (não achei o núcleo). Rode o instalar.sh de novo.",
              file=sys.stderr)
        return 1
    if args.paleta and args.paleta not in PALETAS:
        print(f'❌ Paleta "{args.paleta}" não existe. Use: {", ".join(PALETAS)}.', file=sys.stderr)
        return 1
    try:
        r = gerar(Path(args.projeto), args.paleta)
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
            print("❌ O navegador que desenha o mapa não está instalado. Rode o instalar.sh de novo.", file=sys.stderr)
        else:
            print("❌ Algo deu errado ao desenhar o mapa. Detalhes no log da Máquina (~/.maquina/log).", file=sys.stderr)
        return 1
    p = r["projecao"]
    print(f"✅ Mapa: {r['png']}")
    print(f"   Ticket médio projetado: {brl(p['ticket_medio'])} (+{p['aumento_pct']:.0f}% sobre o produto principal; {'upsell +%.0f%%' % p['aumento_upsell_pct'] if p['aumento_upsell_pct'] else 'sem upsell ainda — a meta de 25–30% é do upsell'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
