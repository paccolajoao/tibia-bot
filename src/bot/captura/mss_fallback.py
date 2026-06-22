"""Capturador via `mss` — Python puro, funciona em qualquer versão/SO.

Mais lento que DXGI (~30-60 FPS de region grab), mas suficiente para auto-heal
(o loop roda a ~15 FPS). É a rede de segurança que garante o MVP rodar mesmo
sem `bettercam` (ex.: Python 3.13).
"""

from __future__ import annotations

import time

import numpy as np

from bot.captura.base import Frame, Regiao


class CapturadorMSS:
    nome_backend = "mss"

    def __init__(self, monitor: int = 0):
        self._monitor_idx = monitor
        self._sct = None

    def iniciar(self) -> None:
        import mss

        self._sct = mss.mss()

    def capturar(self, regiao: Regiao | None = None) -> Frame | None:
        if self._sct is None:
            self.iniciar()
        if regiao is not None:
            left, top, right, bottom = regiao
            box = {"left": left, "top": top, "width": right - left, "height": bottom - top}
        else:
            # monitors[0] = união de todos; monitors[1] = primário
            box = self._sct.monitors[self._monitor_idx + 1]
        bruto = self._sct.grab(box)
        imagem = np.asarray(bruto)[:, :, :3]  # BGRA -> BGR (descarta alfa)
        return Frame(
            imagem=np.ascontiguousarray(imagem),
            ts=time.perf_counter(),
            regiao=regiao,
        )

    def parar(self) -> None:
        if self._sct is not None:
            self._sct.close()
            self._sct = None
