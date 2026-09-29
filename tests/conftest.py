import pytest


@pytest.fixture(autouse=True)
def _isolar_maquina_home(tmp_path_factory, monkeypatch):
    """Nenhum teste pode escrever no ~/.maquina real (log técnico, chaves).
    Testes que usam `ambiente` sobrescrevem com o próprio tmp."""
    monkeypatch.setenv("MAQUINA_HOME", str(tmp_path_factory.mktemp("maquina_home")))
    monkeypatch.setenv("MAQUINA_PROJETOS", str(tmp_path_factory.mktemp("maquina_projetos")))


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("MAQUINA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("MAQUINA_PROJETOS", str(tmp_path / "projetos"))
    # a máquina de dev tem KIE_API_KEY exportada no ~/.zshrc; não pode vazar pros testes
    monkeypatch.delenv("KIE_API_KEY", raising=False)
    monkeypatch.delenv("NETLIFY_TOKEN", raising=False)
    return tmp_path
