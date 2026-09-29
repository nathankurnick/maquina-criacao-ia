import json

import baixar_criativos as bc


def _ad(i, **extra):
    a = {"id": str(i), "pagina": f"Pag{i}", "texto": f"Texto {i}", "cta": "Saiba mais",
         "link": f"https://a.com/{i}", "videos": [f"https://scontent.fbcdn.net/v/{i}.mp4?sig=1"],
         "imagens": [f"https://scontent.fbcdn.net/i/{i}.jpg?sig=2", f"https://scontent.fbcdn.net/i/{i}b.jpg"]}
    a.update(extra)
    return a


def _monta(tmp_path, n=12):
    anuncios = [_ad(i) for i in range(1, n + 1)]
    (tmp_path / "anuncios.json").write_text(json.dumps(anuncios))
    ofertas = {"ofertas": [{"chave": "x.com", "ids": [str(i) for i in range(1, n + 1)]},
                           {"chave": "y.com", "ids": ["3"]}]}
    (tmp_path / "ofertas.json").write_text(json.dumps(ofertas))


def _args(tmp_path, oferta="1"):
    return ["--anuncios", str(tmp_path / "anuncios.json"), "--ofertas", str(tmp_path / "ofertas.json"),
            "--oferta", oferta, "--saida", str(tmp_path / "O" / "anuncios")]


def test_baixa_primeira_imagem_e_primeiro_video_dos_10_primeiros(tmp_path, monkeypatch):
    _monta(tmp_path)
    chamadas = []

    def falso(url, destino):
        chamadas.append(url)
        destino.write_bytes(b"x")
        return True
    monkeypatch.setattr(bc, "baixar", falso)
    assert bc.main(_args(tmp_path)) == 0
    assert len(chamadas) == 20  # 10 anúncios × (1 imagem + 1 vídeo)
    assert not any(u.endswith("b.jpg") for u in chamadas)
    cri = json.loads((tmp_path / "O" / "anuncios" / "criativos.json").read_text())
    assert len(cri) == 10 and cri[0]["id"] == "1"
    assert set(cri[0]) >= {"id", "pagina", "texto", "cta", "link", "arquivos", "biblioteca"}
    assert cri[0]["biblioteca"] == "https://www.facebook.com/ads/library/?id=1"
    assert len(cri[0]["arquivos"]) == 2
    for nome in cri[0]["arquivos"]:
        assert (tmp_path / "O" / "anuncios" / nome).exists()


def test_falha_de_download_segue_e_ainda_grava_criativos(tmp_path, monkeypatch, capsys):
    _monta(tmp_path, 2)
    monkeypatch.setattr(bc, "baixar", lambda url, destino: False)
    assert bc.main(_args(tmp_path)) == 0
    cri = json.loads((tmp_path / "O" / "anuncios" / "criativos.json").read_text())
    assert [c["arquivos"] for c in cri] == [[], []]
    assert "não consegui baixar" in capsys.readouterr().out.lower()


def test_excecao_no_downloader_nao_derruba(tmp_path, monkeypatch):
    _monta(tmp_path, 1)

    def quebra(url, destino):
        raise OSError("boom")
    monkeypatch.setattr(bc, "baixar", quebra)
    assert bc.main(_args(tmp_path)) == 0


def test_oferta_inexistente_sai_1(tmp_path, capsys):
    _monta(tmp_path)
    assert bc.main(_args(tmp_path, "9")) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_arquivo_ilegivel_sai_1(tmp_path, capsys):
    assert bc.main(_args(tmp_path)) == 1
    assert "Não consegui ler" in capsys.readouterr().err


def test_argparse_em_portugues(capsys):
    assert bc.main([]) == 1
    assert "Comando inválido" in capsys.readouterr().err


def test_baixar_real_usa_headers_timeout_e_limite(tmp_path, monkeypatch):
    visto = {}

    class Resp:
        headers = {"Content-Length": "5"}

        def __init__(self, dados):
            self._d = dados

        def read(self, n=-1):
            d, self._d = self._d, b""
            return d

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def urlopen(req, timeout):
        visto["h"] = dict(req.header_items())
        visto["t"] = timeout
        return Resp(b"abcde")
    monkeypatch.setattr(bc.urllib.request, "urlopen", urlopen)
    destino = tmp_path / "a.jpg"
    assert bc.baixar("https://x/a.jpg", destino) is True
    assert destino.read_bytes() == b"abcde"
    assert visto["t"] == 60
    assert visto["h"]["Referer"] == "https://www.facebook.com/" and "Chrome" in visto["h"]["User-agent"]

    Resp.headers = {"Content-Length": str(bc.LIMITE_BYTES + 1)}
    grande = tmp_path / "g.mp4"
    assert bc.baixar("https://x/g.mp4", grande) is False and not grande.exists()


def test_baixar_real_erro_de_rede_devolve_false(tmp_path, monkeypatch):
    def urlopen(req, timeout):
        raise OSError("expirou")
    monkeypatch.setattr(bc.urllib.request, "urlopen", urlopen)
    assert bc.baixar("https://x/a.jpg", tmp_path / "a.jpg") is False


def test_oferta_zero_ou_negativa_sai_1(tmp_path):
    _monta(tmp_path)
    assert bc.main(_args(tmp_path, "0")) == 1
    assert bc.main(_args(tmp_path, "-1")) == 1


def test_so_aceita_http_e_https(tmp_path, monkeypatch):
    anuncios = [_ad(1, videos=["file:///etc/passwd"], imagens=["ftp://x/a.jpg"]),
                _ad(2, videos=[], imagens=["HTTPS://x/a.jpg"])]
    (tmp_path / "anuncios.json").write_text(json.dumps(anuncios))
    (tmp_path / "ofertas.json").write_text(json.dumps({"ofertas": [{"chave": "x", "ids": ["1", "2"]}]}))
    chamadas = []
    monkeypatch.setattr(bc, "baixar", lambda u, d: chamadas.append(u) or d.write_bytes(b"x") or True)
    assert bc.main(_args(tmp_path)) == 0
    assert chamadas == ["HTTPS://x/a.jpg"]


def test_baixar_tem_limite_de_tempo_total(tmp_path, monkeypatch):
    class Resp:
        headers = {}

        def read(self, n=-1):
            return b"x"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(bc.urllib.request, "urlopen", lambda req, timeout: Resp())
    tempos = iter([0, 0, 1000, 2000, 3000])
    monkeypatch.setattr(bc.time, "monotonic", lambda: next(tempos))
    destino = tmp_path / "a.mp4"
    assert bc.baixar("https://x/a.mp4", destino) is False and not destino.exists()
