import pytest


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("MAQUINA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("MAQUINA_PROJETOS", str(tmp_path / "projetos"))
    # a máquina de dev tem KIE_API_KEY exportada no ~/.zshrc; não pode vazar pros testes
    monkeypatch.delenv("KIE_API_KEY", raising=False)
    monkeypatch.delenv("NETLIFY_TOKEN", raising=False)
    return tmp_path
