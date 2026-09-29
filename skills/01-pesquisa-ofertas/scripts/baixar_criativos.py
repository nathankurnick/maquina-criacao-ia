"""Baixa os criativos (imagem + vídeo) dos primeiros anúncios de uma oferta escolhida.

Os links de mídia do Facebook (fbcdn) expiram em horas: rode logo depois de o aluno escolher.
Uso: python baixar_criativos.py --anuncios <B>/anuncios.json --ofertas <B>/ofertas.json
     --oferta N --saida <O>/anuncios
Gera os arquivos baixados + criativos.json (id, pagina, texto, cta, link, arquivos, biblioteca).
"""
import argparse
import json
import os
import sys
import traceback
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
REFERER = "https://www.facebook.com/"
TIMEOUT = 60
LIMITE_BYTES = 60 * 1024 * 1024
MAX_ANUNCIOS = 10
BIBLIOTECA = "https://www.facebook.com/ads/library/?id="


def _log_tecnico(e: BaseException) -> None:
    """Grava o traceback completo em ~/.maquina/log/maquina.log. Nunca levanta erro."""
    try:
        base = Path(os.environ.get("MAQUINA_HOME") or Path.home() / ".maquina") / "log"
        base.mkdir(parents=True, exist_ok=True)
        with (base / "maquina.log").open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] baixar_criativos.py\n")
            f.write("".join(traceback.format_exception(type(e), e, e.__traceback__)) + "\n")
    except Exception:
        pass


def baixar(url: str, destino: Path) -> bool:
    """Baixa url em destino. False se falhar ou passar de 60 MB (nunca deixa arquivo pela metade)."""
    parcial = destino.with_name(destino.name + ".parte")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": REFERER})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            tamanho = resp.headers.get("Content-Length")
            if tamanho and tamanho.isdigit() and int(tamanho) > LIMITE_BYTES:
                return False
            total = 0
            with open(parcial, "wb") as f:
                while True:
                    pedaco = resp.read(1024 * 256)
                    if not pedaco:
                        break
                    total += len(pedaco)
                    if total > LIMITE_BYTES:
                        return False
                    f.write(pedaco)
        parcial.replace(destino)
        return True
    except Exception:
        return False
    finally:
        try:
            parcial.unlink(missing_ok=True)
        except OSError:
            pass


def _extensao(url: str, padrao: str) -> str:
    sufixo = Path(urlparse(url).path).suffix.lower()
    return sufixo if sufixo in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".webm") else padrao


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        if "required" in message:
            message = "faltou informar --anuncios, --ofertas, --oferta e --saida"
        elif "expected one argument" in message:
            message = "faltou o valor de uma opção (" + message.split(":")[0].replace("argument ", "") + ")"
        else:
            message = "opção não reconhecida"
        print(f"❌ Comando inválido: {message}. Use: baixar_criativos.py --anuncios <anuncios.json> "
              "--ofertas <ofertas.json> --oferta N --saida <pasta>.", file=sys.stderr)
        raise SystemExit(1)


def _ler_json(caminho: str):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        _log_tecnico(e)
        print(f"❌ Não consegui ler {caminho} ({type(e).__name__}). Rode a pesquisa de novo.", file=sys.stderr)
        return None


def main(argv: "list[str] | None" = None) -> int:
    ap = _Parser(description="Baixa os criativos da oferta escolhida.")
    ap.add_argument("--anuncios", required=True)
    ap.add_argument("--ofertas", required=True)
    ap.add_argument("--oferta", required=True, type=str)
    ap.add_argument("--saida", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 1

    anuncios, ofertas = _ler_json(args.anuncios), _ler_json(args.ofertas)
    if not isinstance(anuncios, list) or not isinstance(ofertas, dict):
        if anuncios is not None and ofertas is not None:
            print("❌ Arquivos de pesquisa em formato inesperado. Rode a pesquisa de novo.", file=sys.stderr)
        return 1
    try:
        n = int(args.oferta)
        if n < 1:
            raise IndexError
        oferta = ofertas["ofertas"][n - 1]
        ids = [str(i) for i in oferta.get("ids", [])][:MAX_ANUNCIOS]
    except (KeyError, IndexError, ValueError, TypeError, AttributeError):
        print(f"❌ Não existe a oferta '{args.oferta}' nesse ranking. Escolha um número da tabela.",
              file=sys.stderr)
        return 1
    por_id = {}
    for pos, a in enumerate(anuncios, start=1):
        if isinstance(a, dict):
            por_id.setdefault(str(a.get("id") or f"pos{pos}"), a)
    saida = Path(args.saida)
    try:
        saida.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        _log_tecnico(e)
        print(f"❌ Não consegui gravar na pasta {saida}. Escolha outra pasta.", file=sys.stderr)
        return 1

    def seguro(nome: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in nome)

    criativos, baixados = [], 0
    print("⬇️ Baixando os criativos dos anúncios da oferta...")
    for aid in ids:
        a = por_id.get(aid)
        if a is None:
            continue
        arquivos = []
        for tipo, campo, padrao in (("imagem", "imagens", ".jpg"), ("video", "videos", ".mp4")):
            urls = a.get(campo)
            url = urls[0] if isinstance(urls, list) and urls and isinstance(urls[0], str) else ""
            if not url:
                continue
            nome = f"{seguro(aid)}-{tipo}{_extensao(url, padrao)}"
            try:
                ok = baixar(url, saida / nome)
            except Exception as e:  # um arquivo ruim não derruba os outros
                _log_tecnico(e)
                ok = False
            if ok:
                arquivos.append(nome)
                baixados += 1
        criativos.append({
            "id": aid, "pagina": str(a.get("pagina") or ""), "texto": str(a.get("texto") or ""),
            "cta": str(a.get("cta") or ""), "link": str(a.get("link") or ""),
            "arquivos": arquivos, "biblioteca": BIBLIOTECA + aid,
        })
    if not criativos:
        print("❌ Não achei os anúncios dessa oferta em anuncios.json. Rode a pesquisa de novo.", file=sys.stderr)
        return 1
    try:
        (saida / "criativos.json").write_text(json.dumps(criativos, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        _log_tecnico(e)
        print(f"❌ Não consegui salvar criativos.json em {saida}.", file=sys.stderr)
        return 1
    if baixados:
        print(f"✅ {baixados} arquivos baixados de {len(criativos)} anúncios → {saida}")
    else:
        print("⚠️ Não consegui baixar nenhum arquivo (os links de mídia do Facebook expiram em poucas horas). "
              f"Salvei só os textos e os links da Biblioteca em {saida / 'criativos.json'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
