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
     re.compile(r"\bvoc[eê]\s+(est[aá]|[eé]|e|tem|sofre|anda)\b[^.!?]{0,30}\b(gord|acima do peso|sobrepeso|obes|calv|endividad|quebrad|deprimid|ansios|diabet|velh|fei[oa]|fl[aá]cid)", _I)),
    ("Antes e depois: costuma ser reprovado. Dica: mostre o processo, não a comparação.",
     re.compile(r"\bantes\s*(e|/|x|&)\s*depois\b", _I)),
    ("Promessa de ganho com valor: alto risco de reprovação. Dica: fale do que o produto ensina.",
     re.compile(r"\b(ganh|fatur|lucr|renda)\w*\b[^.!?]{0,30}(R\$\s?\d|\b\d+\s*mil\b)", _I)),
    ("Resultado garantido: a Meta costuma barrar. Dica: garanta a devolução do dinheiro, não o resultado.",
     re.compile(r"\bresultados?\s+(100%\s+)?garantid|\b(100%|sucesso|lucro|emagrecimento|dinheiro|ganhos?)\s+garantid|\bgarantid[oa]s?\s+(resultados?|sucesso|lucro|emagrecimento|dinheiro|ganhos?)\b", _I)),
    ("Prazo de resultado: 'perca X em Y dias' é sensível. Dica: tire o prazo ou fale da rotina.",
     re.compile(r"\b(emagre[cç]a\b[^.!?]{0,40}|(perca|elimine|ganhe)\b[^.!?]{0,40}(?<![a-zà-ú])(kg|quilos?|peso|barriga|gordura|medidas|cm|R\$|reais|dinheiro|mil)(?![a-zà-ú])[^.!?]{0,20})\bem\s+\d+\s+(dias|semanas)", _I)),
    ("Cura/saúde: promessa de curar doença é reprovada. Dica: fale de hábito e bem-estar.",
     re.compile(r"\b(cura|cure|curar|elimina|acabe com|reverte)\b[^.!?]{0,30}\b(diabetes|press[aã]o|ansiedade|depress[aã]o|doen[cç]a|c[aâ]ncer)", _I)),
    ("Idade/gênero no texto: chamar o público por idade ou gênero pode ser lido como atributo pessoal.",
     re.compile(r"\b(mulheres|homens)\s+(acima|com mais)\s+d[eo]s?\s+\d+\b(?!\s+anos\s+de\s+(experi|mercado|carreira|estrada|hist|atua|vida))", _I)),
    ("Isca de clique: 'clique aqui', 'últimas vagas', 'só hoje' reduzem a entrega e podem reprovar.",
     re.compile(r"\b(clique aqui|[uú]ltimas?\s+vagas|s[oó]\s+hoje|corre que)\b", _I)),
]


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        if "required" in message or "obrigat" in message:
            motivo = "falta --pasta"
        elif "unrecognized" in message:
            motivo = "opção desconhecida"
        else:
            motivo = "argumento inválido"
        print(f"❌ Comando incompleto ({motivo}). Use: anuncio_riscos.py --pasta <P>/anuncios", file=sys.stderr)
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
    if len(anuncio.get("titulo") or "") > 40:
        avisos.append("Título longo: mais de 40 caracteres é cortado no feed.")
    return avisos


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Avisa riscos de reprovação na Meta.", add_help=False)
    ap.add_argument("-h", "--help", action="help", help="mostra esta ajuda")
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
    except KeyboardInterrupt:
        print("Cancelado.", file=sys.stderr)
        return 130
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
