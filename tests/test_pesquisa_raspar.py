import json

import raspar
from coleta import Coletor


def _html(aid):
    ad = {"ad_archive_id": aid, "snapshot": {"page_name": "P", "link_url": "https://x.com",
                                             "body": {"text": "Texto qualquer do anúncio"}}}
    return f'<script type="application/json">{json.dumps({"a": ad})}</script>'


class _Botao:
    def __init__(self, pagina, nome):
        self.first, self._p, self._n = self, pagina, nome

    def click(self, timeout):
        self._p.cliques.append(self._n)
        if self._n != "Allow all":
            raise TimeoutError("não achou")


class _Mouse:
    def __init__(self, p):
        self._p = p

    def wheel(self, x, y):
        self._p.rolagens += 1


class PaginaFalsa:
    def __init__(self):
        self.rolagens, self.cliques, self.esperas = 0, [], 0
        self.mouse = _Mouse(self)

    def wait_for_timeout(self, ms):
        self.esperas += 1

    def get_by_role(self, role, name):
        return _Botao(self, name)

    def content(self):
        # cada rolagem "carrega" um anúncio novo, e o DOM virtualizado some com os antigos
        return _html(f"ad{self.rolagens}")


def test_rolar_e_coletar_rola_aceita_cookies_e_colhe_durante():
    p, c = PaginaFalsa(), Coletor()
    raspar.rolar_e_coletar(p, c, rolagens=7)
    assert p.rolagens == 7
    assert p.cliques[:2] == ["Allow all cookies", "Allow all"]
    # colhe no início (0), a cada 3 rolagens (após 1, 4, 7) e no fim (7 de novo, dedup)
    assert [a["id"] for a in c.anuncios] == ["ad0", "ad1", "ad4", "ad7"]


def test_main_sem_anuncios_sai_com_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(raspar, "abrir_e_coletar", lambda url, rolagens: [])
    assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "nenhum anúncio" in err and "links" in err


def test_main_grava_anuncios_e_busca(tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(raspar, "abrir_e_coletar",
                        lambda url, rolagens: chamadas.append((url, rolagens)) or [{"id": "1"}])
    assert raspar.main(["--dominio", "loja.com", "--rolagens", "5", "--saida", str(tmp_path / "s")]) == 0
    assert chamadas[0][1] == 5 and "q=loja.com%2F" in chamadas[0][0]
    assert json.loads((tmp_path / "s" / "anuncios.json").read_text()) == [{"id": "1"}]
    busca = json.loads((tmp_path / "s" / "busca.json").read_text())
    assert busca["total"] == 1 and busca["url"] == chamadas[0][0] and busca["data"]


def test_main_url_direta(tmp_path, monkeypatch):
    urls = []
    monkeypatch.setattr(raspar, "abrir_e_coletar", lambda url, rolagens: urls.append(url) or [{"id": "1"}])
    raspar.main(["--url", "https://www.facebook.com/ads/library/?id=123", "--saida", str(tmp_path)])
    assert urls == ["https://www.facebook.com/ads/library/?id=123"]


def test_main_navegador_quebrado_mensagem_amigavel(tmp_path, monkeypatch, capsys):
    def quebra(url, rolagens):
        raise RuntimeError("Executable doesn't exist")
    monkeypatch.setattr(raspar, "abrir_e_coletar", quebra)
    assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "navegador" in err and "Traceback" not in err


def test_main_exige_um_criterio(tmp_path, capsys):
    assert raspar.main(["--saida", str(tmp_path)]) == 1
    assert "termo" in capsys.readouterr().err
