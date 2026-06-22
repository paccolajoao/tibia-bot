"""Testes do backend WGC — só a adaptação callback->pull (sem display/GPU).

A captura real (Windows Graphics Capture) precisa de tela/GPU e é validada com o
jogo; aqui cobrimos a interface e o recorte de região injetando um frame fake.
"""

from __future__ import annotations

import numpy as np

from bot.captura.base import CapturadorBase
from bot.captura.wgc import CapturadorWGC


def test_interface_e_sem_frame():
    cap = CapturadorWGC(monitor=0)
    assert cap.nome_backend == "wgc"
    assert isinstance(cap, CapturadorBase)  # satisfaz o Protocol
    # nenhum frame ainda -> None (o loop tolera e tenta de novo)
    assert cap.capturar() is None
    assert cap.capturar((0, 0, 10, 10)) is None
    cap.parar()  # sem sessão -> no-op


def test_capturar_recorta_regiao():
    cap = CapturadorWGC()
    cap._ultimo = np.zeros((100, 200, 3), np.uint8)  # frame fake (full monitor)
    frame = cap.capturar((10, 20, 60, 50))  # (left, top, right, bottom)
    assert frame is not None
    assert frame.imagem.shape == (30, 50, 3)  # (bottom-top, right-left)
    assert frame.regiao == (10, 20, 60, 50)


def test_capturar_sem_regiao_devolve_frame_inteiro():
    cap = CapturadorWGC()
    cap._ultimo = np.zeros((90, 160, 3), np.uint8)
    frame = cap.capturar(None)
    assert frame is not None
    assert frame.imagem.shape == (90, 160, 3)
    assert frame.regiao is None
