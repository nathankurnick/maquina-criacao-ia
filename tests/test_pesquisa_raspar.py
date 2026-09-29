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


OFERTA_MANUAL = "Se preferir, cole aqui os links dos anúncios ou das páginas de vendas que você achou e eu sigo no modo manual."


def _fake(anuncios, interrompido=False):
    def f(url, rolagens, coletor=None):
        return anuncios, interrompido
    return f


def test_main_sem_anuncios_sai_com_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(raspar, "abrir_e_coletar", _fake([]))
    assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "nenhum anúncio" in err and "links" in err


def test_main_grava_anuncios_e_busca(tmp_path, monkeypatch):
    chamadas = []

    def f(url, rolagens, coletor=None):
        chamadas.append((url, rolagens))
        return [{"id": "1"}], False
    monkeypatch.setattr(raspar, "abrir_e_coletar", f)
    assert raspar.main(["--dominio", "loja.com", "--rolagens", "5", "--saida", str(tmp_path / "s")]) == 0
    assert chamadas[0][1] == 5 and "q=loja.com%2F" in chamadas[0][0]
    assert json.loads((tmp_path / "s" / "anuncios.json").read_text()) == [{"id": "1"}]
    busca = json.loads((tmp_path / "s" / "busca.json").read_text())
    assert busca["total"] == 1 and busca["url"] == chamadas[0][0] and busca["data"]


def test_main_url_direta(tmp_path, monkeypatch, capsys):
    urls = []

    def f(url, rolagens, coletor=None):
        urls.append(url)
        return [{"id": "1"}], False
    monkeypatch.setattr(raspar, "abrir_e_coletar", f)
    raspar.main(["--url", "https://www.facebook.com/ads/library/?id=123", "--saida", str(tmp_path)])
    assert urls == ["https://www.facebook.com/ads/library/?id=123"]
    assert "URL" not in capsys.readouterr().out.split("Abrindo")[0]


def test_main_url_com_termo_avisa(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(raspar, "abrir_e_coletar", _fake([{"id": "1"}]))
    raspar.main(["--url", "https://x.com/ads", "--termo", "abc", "--saida", str(tmp_path)])
    assert "usei a URL" in capsys.readouterr().out


def _quebra(exc):
    def f(url, rolagens, coletor=None):
        raise exc
    return f


def test_main_navegador_quebrado_mensagem_amigavel(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(raspar, "abrir_e_coletar", _quebra(RuntimeError("Executable doesn't exist")))
    assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "instalar.sh" in err and "Traceback" not in err and OFERTA_MANUAL in err


def test_main_playwright_ausente(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(raspar, "abrir_e_coletar", _quebra(ModuleNotFoundError("playwright")))
    assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "instalar.sh" in err and OFERTA_MANUAL in err


def test_main_timeout_mensagem(tmp_path, monkeypatch, capsys):
    class TimeoutError(Exception):
        pass
    for exc in (TimeoutError("x"), RuntimeError("net::ERR_INTERNET_DISCONNECTED")):
        monkeypatch.setattr(raspar, "abrir_e_coletar", _quebra(exc))
        assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 1
        err = capsys.readouterr().err
        assert "demorou demais" in err and "instalar.sh" not in err and OFERTA_MANUAL in err


def test_main_erro_generico_tem_oferta_manual(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(raspar, "abrir_e_coletar", _quebra(ValueError("boom")))
    assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 1
    assert OFERTA_MANUAL in capsys.readouterr().err


def test_main_exige_um_criterio(tmp_path, capsys):
    assert raspar.main(["--saida", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "termo" in err and OFERTA_MANUAL in err


def test_main_parada_antecipada_salva_parcial(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(raspar, "abrir_e_coletar", _fake([{"id": "1"}, {"id": "2"}], True))
    assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "parou antes do fim, mas salvei os 2 anúncios" in out
    assert len(json.loads((tmp_path / "anuncios.json").read_text())) == 2


def test_main_ctrl_c_salva_parcial_e_sai_130(tmp_path, monkeypatch, capsys):
    def f(url, rolagens, coletor=None):
        coletor.anuncios.append({"id": "9"})
        raise KeyboardInterrupt
    monkeypatch.setattr(raspar, "abrir_e_coletar", f)
    assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 130
    cap = capsys.readouterr()
    assert "Pesquisa cancelada." in cap.err and "Traceback" not in cap.err
    assert json.loads((tmp_path / "anuncios.json").read_text()) == [{"id": "9"}]


def test_main_ctrl_c_sem_anuncios(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(raspar, "abrir_e_coletar", _quebra(KeyboardInterrupt()))
    assert raspar.main(["--termo", "x", "--saida", str(tmp_path)]) == 130
    assert "Pesquisa cancelada." in capsys.readouterr().err
    assert not (tmp_path / "anuncios.json").exists()


def test_argparse_saida_ausente_sai_1_em_portugues(capsys):
    assert raspar.main(["--termo", "x"]) == 1
    err = capsys.readouterr().err
    assert "--saida" in err and "required" not in err and "usage" not in err.lower()


def test_rolagens_zero_sai_1(tmp_path, capsys):
    assert raspar.main(["--termo", "x", "--rolagens", "0", "--saida", str(tmp_path)]) == 1
    assert "--rolagens" in capsys.readouterr().err


def test_saida_nao_gravavel_sai_1_antes_do_navegador(tmp_path, monkeypatch, capsys):
    arq = tmp_path / "arquivo"
    arq.write_text("x")
    chamou = []
    monkeypatch.setattr(raspar, "abrir_e_coletar", lambda *a, **k: chamou.append(1) or ([], False))
    assert raspar.main(["--termo", "x", "--saida", str(arq / "sub")]) == 1
    assert not chamou and "pasta" in capsys.readouterr().err


class _Ctx:
    def __init__(self, falha_em):
        self.falha_em = falha_em

    def new_page(self):
        return _PagFalha(self.falha_em)


class _PagFalha(PaginaFalsa):
    def __init__(self, falha_em):
        super().__init__()
        self.falha_em = falha_em

    def on(self, *a):
        pass

    def goto(self, *a, **k):
        if self.falha_em == "goto":
            raise RuntimeError("net::ERR_FAILED")

    def content(self):
        if self.rolagens >= 2:
            raise RuntimeError("Target page, context or browser has been closed")
        return super().content()


class _Nav:
    def __init__(self, falha_em):
        self.falha_em = falha_em

    def new_context(self, **k):
        return _Ctx(self.falha_em)

    def close(self):
        raise RuntimeError("já morreu")


def _instala_playwright_falso(monkeypatch, falha_em):
    import sys
    import types
    mod = types.ModuleType("playwright.sync_api")

    class _P:
        chromium = types.SimpleNamespace(launch=lambda **k: _Nav(falha_em))

    class _CM:
        def __enter__(self):
            return _P()

        def __exit__(self, *a):
            return False
    mod.sync_playwright = lambda: _CM()
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", mod)


def test_abrir_e_coletar_devolve_parcial_se_falha_apos_goto(monkeypatch):
    _instala_playwright_falso(monkeypatch, "rolagem")
    anuncios, interrompido = raspar.abrir_e_coletar("https://x", 10)
    assert interrompido is True and [a["id"] for a in anuncios] == ["ad0", "ad1"]


def test_abrir_e_coletar_falha_no_goto_propaga_e_close_nao_mascara(monkeypatch):
    import pytest
    _instala_playwright_falso(monkeypatch, "goto")
    with pytest.raises(RuntimeError, match="net::"):
        raspar.abrir_e_coletar("https://x", 10)
