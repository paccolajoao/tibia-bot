"""Testes do backend Arduino — OFFLINE, com uma serial FALSA (sem hardware)."""

from __future__ import annotations

import pytest

from bot.entrada.teclado_arduino import EntradaArduino, EntradaArduinoErro, executar_diagnostico


class SerialFalsa:
    """Fake de `serial.Serial`: fila de respostas de entrada + log do que foi escrito."""

    def __init__(self, respostas: list[str]):
        self._respostas = list(respostas)
        self.escritas: list[bytes] = []
        self.fechada = False

    def write(self, dados: bytes) -> None:
        self.escritas.append(dados)

    def readline(self) -> bytes:
        if not self._respostas:
            return b""  # simula timeout (pyserial devolve vazio)
        return self._respostas.pop(0).encode("ascii")

    def close(self) -> None:
        self.fechada = True


LARGURA, ALTURA = 1920, 1080


def _escalar_esperado(x: int, y: int) -> tuple[int, int]:
    """Réplica independente da fórmula de escala p/ o range 0-32767 do HID absoluto."""
    hx = round(x * 32767 / (LARGURA - 1))
    hy = round(y * 32767 / (ALTURA - 1))
    return hx, hy


def _entrada(respostas, **kw) -> tuple[EntradaArduino, SerialFalsa]:
    ser = SerialFalsa(["READY\n", *respostas])
    ent = EntradaArduino("COM_FAKE", largura_tela=LARGURA, altura_tela=ALTURA, serial_obj=ser, **kw)
    return ent, ser


def test_aguarda_ready_ao_conectar():
    ent, ser = _entrada([])
    assert ser.escritas == []  # nada enviado ainda, só o handshake de leitura


def test_sem_ready_levanta():
    ser = SerialFalsa(["algo estranho\n"])
    with pytest.raises(EntradaArduinoErro, match="READY"):
        EntradaArduino("COM_FAKE", serial_obj=ser)


def test_pressionar_tecla_envia_comando_k():
    ent, ser = _entrada(["OK\n"], atraso_pre_ms=(0, 0), atraso_pos_ms=(0, 0))
    ent.pressionar_tecla("f1")
    assert ser.escritas == [b"K F1\n"]


def test_clicar_escala_coordenadas_para_faixa_hid():
    ent, ser = _entrada(["OK\n"], atraso_pre_ms=(0, 0), atraso_pos_ms=(0, 0))
    ent.clicar(0, 0)
    assert ser.escritas == [b"M 0 0\n"]


def test_clicar_no_canto_oposto_escala_para_32767():
    ent, ser = _entrada(["OK\n"], atraso_pre_ms=(0, 0), atraso_pos_ms=(0, 0))
    ent.clicar(1919, 1079)  # último pixel válido (largura-1, altura-1)
    assert ser.escritas == [b"M 32767 32767\n"]


def test_clicar_direito_envia_comando_mr():
    ent, ser = _entrada(["OK\n"], atraso_pre_ms=(0, 0), atraso_pos_ms=(0, 0))
    ent.clicar_direito(960, 540)
    hx, hy = _escalar_esperado(960, 540)
    assert ser.escritas == [f"MR {hx} {hy}\n".encode("ascii")]


def test_arrastar_envia_comando_d():
    ent, ser = _entrada(["OK\n"], atraso_pre_ms=(0, 0), atraso_pos_ms=(0, 0))
    ent.arrastar(100, 200, 1919, 1079)
    hx1, hy1 = _escalar_esperado(100, 200)
    assert ser.escritas == [f"D {hx1} {hy1} 32767 32767\n".encode("ascii")]


def test_resposta_err_levanta():
    ent, ser = _entrada(["ERR tecla desconhecida\n"], atraso_pre_ms=(0, 0), atraso_pos_ms=(0, 0))
    with pytest.raises(EntradaArduinoErro, match="ERR"):
        ent.pressionar_tecla("teclanaoexiste")


def test_sem_resposta_levanta_timeout():
    ent, ser = _entrada([], atraso_pre_ms=(0, 0), atraso_pos_ms=(0, 0))
    with pytest.raises(EntradaArduinoErro, match="sem resposta"):
        ent.pressionar_tecla("f1")


def test_ping_envia_p_e_retorna_latencia():
    ent, ser = _entrada(["PONG\n"])
    latencia = ent.ping()
    assert ser.escritas == [b"P\n"]
    assert latencia >= 0


def test_mover_envia_comando_mv_sem_clicar():
    ent, ser = _entrada(["OK\n"])
    ent.mover(0, 0)
    assert ser.escritas == [b"MV 0 0\n"]


def test_fechar_fecha_a_serial():
    ent, ser = _entrada([])
    ent.fechar()
    assert ser.fechada


# --------------------------------------------------------------- executar_diagnostico

def test_diagnostico_sucesso_sem_teste_de_clique():
    ser = SerialFalsa(["READY\n", "PONG\n", "OK\n", "OK\n"])  # conectar, ping, teclado, mouse_movimento
    resultado = executar_diagnostico("COM_FAKE", largura_tela=1920, altura_tela=1080, serial_obj=ser)

    assert resultado["sucesso"] is True
    nomes = [e["nome"] for e in resultado["etapas"]]
    assert nomes == ["conectar", "ping", "teclado", "mouse_movimento"]
    assert all(e["ok"] for e in resultado["etapas"])
    assert resultado["largura_usada"] == 1920
    assert resultado["altura_usada"] == 1080
    assert ser.fechada
    # a etapa de teclado usa CAPSLOCK — reversível, sem digitar texto
    assert b"K CAPSLOCK\n" in ser.escritas
    # mouse_movimento mira o centro da tela, sem clicar (comando MV, não M)
    hx, hy = _escalar_esperado(1920 // 2, 1080 // 2)
    assert f"MV {hx} {hy}\n".encode("ascii") in ser.escritas


def test_diagnostico_com_clique_real_quando_habilitado():
    ser = SerialFalsa(["READY\n", "PONG\n", "OK\n", "OK\n", "OK\n"])
    resultado = executar_diagnostico(
        "COM_FAKE", largura_tela=1920, altura_tela=1080, serial_obj=ser,
        testar_clique=True, ponto_clique=(100, 200),
    )
    nomes = [e["nome"] for e in resultado["etapas"]]
    assert nomes == ["conectar", "ping", "teclado", "mouse_movimento", "mouse_clique"]
    assert resultado["sucesso"] is True
    hx, hy = _escalar_esperado(100, 200)
    assert f"M {hx} {hy}\n".encode("ascii") in ser.escritas


def test_diagnostico_clique_sem_coordenadas_marca_falha_sem_abortar():
    ser = SerialFalsa(["READY\n", "PONG\n", "OK\n", "OK\n"])
    resultado = executar_diagnostico(
        "COM_FAKE", largura_tela=1920, altura_tela=1080, serial_obj=ser,
        testar_clique=True, ponto_clique=None,
    )
    etapa_clique = next(e for e in resultado["etapas"] if e["nome"] == "mouse_clique")
    assert etapa_clique["ok"] is False
    assert resultado["sucesso"] is False


def test_diagnostico_conexao_falha_reporta_etapa_unica():
    class SerialQueNuncaConecta:
        def write(self, _dados):
            pass

        def readline(self):
            return b""  # nunca manda READY

        def close(self):
            pass

    resultado = executar_diagnostico("COM_FAKE", serial_obj=SerialQueNuncaConecta())
    assert resultado["sucesso"] is False
    assert len(resultado["etapas"]) == 1
    assert resultado["etapas"][0]["nome"] == "conectar"
    assert resultado["etapas"][0]["ok"] is False


def test_diagnostico_uma_etapa_falha_nao_aborta_as_seguintes():
    # ping falha (ERR), mas teclado e mouse_movimento ainda rodam e são reportados
    ser = SerialFalsa(["READY\n", "ERR falha\n", "OK\n", "OK\n"])
    resultado = executar_diagnostico("COM_FAKE", largura_tela=1920, altura_tela=1080, serial_obj=ser)
    por_nome = {e["nome"]: e["ok"] for e in resultado["etapas"]}
    assert por_nome == {"conectar": True, "ping": False, "teclado": True, "mouse_movimento": True}
    assert resultado["sucesso"] is False
