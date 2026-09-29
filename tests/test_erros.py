from nucleo import caminhos
from nucleo.erros import MaquinaErro, registrar_log


def test_caminhos_respeitam_env(ambiente):
    assert caminhos.maquina_home() == ambiente / "home"
    assert caminhos.pasta_projetos() == ambiente / "projetos"


def test_registrar_log_acrescenta_linha(ambiente):
    p = registrar_log("primeiro")
    registrar_log("segundo")
    texto = p.read_text()
    assert p == ambiente / "home" / "log" / "maquina.log"
    assert "primeiro" in texto and "segundo" in texto


def test_maquina_erro_guarda_mensagem():
    assert str(MaquinaErro("Olá")) == "Olá"
