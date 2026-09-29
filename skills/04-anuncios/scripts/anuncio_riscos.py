"""Avisa (não bloqueia) o que costuma levar anúncio a ser reprovado na Meta. O aluno decide.

Uso: python anuncio_riscos.py --pasta <P>/anuncios
"""
import argparse
import re
import sys
from pathlib import Path

from anuncio_dados import ler_anuncios

_I = re.IGNORECASE
REGRAS = [
    ("Atributo pessoal: a Meta reprova anúncio que diz que a pessoa TEM um problema. Dica: fale da situação, não da pessoa.",
     re.compile(r"\bvoc[eê]\s+(est[aá]|[eé]|tem|sofre|anda)\b[^.!?]{0,30}\b(gord|acima do peso|obes|calv|endividad|quebrad|deprimid|ansios|diab[eé]tic|velh|fei[oa]|fl[aá]cid)", _I)),
    ("Antes e depois: costuma ser reprovado. Dica: mostre o processo, não a comparação.",
     re.compile(r"\bantes\s*(e|/|x|&)\s*depois\b", _I)),
    ("Promessa de ganho com valor: alto risco de reprovação. Dica: fale do que o produto ensina.",
     re.compile(r"\b(ganh|fatur|lucr|renda)\w*\b[^.!?]{0,30}R\$\s?\d", _I)),
    ("Resultado garantido: a Meta costuma barrar. Dica: garanta a devolução do dinheiro, não o resultado.",
     re.compile(r"\bresultados?\s+(100%\s+)?garantid|\b(100%|sucesso|lucro|emagrecimento|ganhos?)\s+garantid|\bgarantid[oa]s?\s+(resultados?|sucesso|lucro|emagrecimento|ganhos?)\b", _I)),
    ("Prazo de resultado: 'perca X em Y dias' é sensível. Dica: tire o prazo ou fale da rotina.",
     re.compile(r"\b(emagre[cç]a\b[^.!?]{0,40}|(perca|elimine|ganhe)\b[^.!?]{0,40}\b(kg|quilos?|peso|barriga|gordura|medidas|cm|R\$|reais|dinheiro|mil)\b[^.!?]{0,20})\bem\s+\d+\s+(dias|semanas)", _I)),
    ("Cura/saúde: promessa de curar doença é reprovada. Dica: fale de hábito e bem-estar.",
     re.compile(r"\b(cura|curar|elimina|acabe com|reverte)\b[^.!?]{0,30}\b(diabetes|press[aã]o|ansiedade|depress[aã]o|doen[cç]a|c[aâ]ncer)", _I)),
    ("Idade/gênero no texto: chamar o público por idade ou gênero pode ser lido como atributo pessoal.",
     re.compile(r"\b(mulheres|homens)\s+(acima|com mais)\s+de\s+\d+\b(?!\s+anos\s+de\s+(experi|mercado|carreira|estrada|hist|atua|vida))", _I)),
    ("Isca de clique: 'clique aqui', 'últimas vagas', 'só hoje' reduzem a entrega e podem reprovar.",
     re.compile(r"\b(clique aqui|[uú]ltimas?\s+vagas|s[oó]\s+hoje|corre que)\b", _I)),
]


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"❌ Comando incompleto ({message}). Use: anuncio_riscos.py --pasta <P>/anuncios", file=sys.stderr)
        raise SystemExit(1)


def avaliar(anuncio: dict) -> list[str]:
    partes = [anuncio.get(k) or "" for k in ("headline_imagem", "texto_principal", "titulo", "descricao",
                                             "corpo", "cta_falado")]
    partes += list(anuncio.get("hooks") or [])
    texto = "\n".join(p for p in partes if isinstance(p, str))
    avisos = [msg for msg, padrao in REGRAS if padrao.search(texto)]
    headline = anuncio.get("headline_imagem") or ""
    if len(headline.split()) > 12:
        avisos.append("Texto demais na imagem: mais de 12 palavras na headline da arte reduz a entrega. Dica: corte pra até 8.")
    return avisos


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Avisa riscos de reprovação na Meta.")
    ap.add_argument("--pasta", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as s:
        return int(s.code or 0)
    try:
        anuncios = ler_anuncios(Path(args.pasta))
    except ValueError as err:
        print(f"❌ {err}", file=sys.stderr)
        return 1
    for a in anuncios:
        avisos = avaliar(a)
        if not avisos:
            print(f"{a['id']}: nenhum aviso.")
            continue
        print(f"{a['id']}:")
        for aviso in avisos:
            print(f"   ⚠️ {aviso}")
    print("\nSão só avisos: quem decide se muda é você.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
