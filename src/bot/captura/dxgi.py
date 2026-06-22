"""Capturador via `bettercam` (DXGI Desktop Duplication) — alta taxa de FPS no Windows.

`grab()` retorna None quando o frame não mudou desde a última captura; nesse caso
devolvemos o último frame válido (uma barra estática legitimamente não gera frame novo).
"""

from __future__ import annotations

import time

import numpy as np

from bot.captura.base import Frame, Regiao


class CapturadorDXGI:
    nome_backend = "bettercam"

    def __init__(self, monitor: int = 0):
        self._monitor = monitor
        self._cam = None
        self._ultimo: Frame | None = None

    def iniciar(self) -> None:
        import bettercam

        self._cam = bettercam.create(output_idx=self._monitor, output_color="BGR")

    def capturar(self, regiao: Regiao | None = None) -> Frame | None:
        if self._cam is None:
            self.iniciar()
        imagem = self._cam.grab(region=regiao)  # region = (l, t, r, b) ou None
        if imagem is None:
            return self._ultimo  # frame inalterado -> reusa o último
        frame = Frame(
            imagem=np.ascontiguousarray(imagem),
            ts=time.perf_counter(),
            regiao=regiao,
        )
        self._ultimo = frame
        return frame

    def parar(self) -> None:
        if self._cam is not None:
            try:
                self._cam.release()
            except Exception:
                pass
            self._cam = None
