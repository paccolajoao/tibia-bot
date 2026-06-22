"""Capturador via Windows Graphics Capture (lib `windows-capture`).

Funciona no **Python 3.13** e captura conteúdo acelerado por GPU
(DX11/DX12/OpenGL/Vulkan) que o GDI/`mss` NÃO consegue ler (volta preto). É a saída
para clientes em DirectX 12.

A lib é baseada em CALLBACK numa thread dedicada (`start_free_threaded`); adaptamos
para o modelo PULL do bot guardando sempre o ÚLTIMO frame sob lock. O `frame_buffer`
entregue é uma *view* em memória nativa válida só durante o callback — por isso
**copiamos** na hora.

Captura o MONITOR inteiro (mesmo espaço de coordenadas absolutas do `mss`), então as
regiões calibradas valem igual. Use o Tibia em **janela / sem bordas** — fullscreen
exclusivo ignora o compositor do Windows e some até para captura de GPU.
"""

from __future__ import annotations

import threading
import time

import numpy as np

from bot.captura.base import Frame, Regiao


class CapturadorWGC:
    nome_backend = "wgc"

    def __init__(
        self,
        monitor: int = 0,
        intervalo_min_ms: int = 33,  # ~30 FPS: limita o uso de CPU
        timeout_primeiro_frame_s: float = 5.0,
    ):
        self._monitor_index = monitor + 1  # windows-capture é 1-based (1 = primário)
        self._intervalo_min_ms = intervalo_min_ms
        self._timeout = timeout_primeiro_frame_s
        self._lock = threading.Lock()
        self._ultimo: np.ndarray | None = None
        self._control = None
        self._capture = None

    def iniciar(self) -> None:
        from windows_capture import WindowsCapture

        self._capture = WindowsCapture(
            cursor_capture=False,
            draw_border=False,
            minimum_update_interval=self._intervalo_min_ms,
            monitor_index=self._monitor_index,
        )

        @self._capture.event
        def on_frame_arrived(frame, capture_control):
            # frame_buffer: HxWx4 BGRA (view nativa -> copiar já); [:, :, :3] = BGR
            bgr = np.ascontiguousarray(frame.frame_buffer[:, :, :3])
            with self._lock:
                self._ultimo = bgr

        @self._capture.event
        def on_closed():
            pass

        self._control = self._capture.start_free_threaded()

        # espera o 1º frame: a calibração captura 1x e falharia se viesse None
        prazo = time.perf_counter() + self._timeout
        while time.perf_counter() < prazo:
            with self._lock:
                if self._ultimo is not None:
                    return
            time.sleep(0.03)
        raise RuntimeError("WGC não entregou frame no tempo esperado")

    def capturar(self, regiao: Regiao | None = None) -> Frame | None:
        with self._lock:
            img = self._ultimo
        if img is None:
            return None
        if regiao is not None:
            left, top, right, bottom = regiao
            img = img[top:bottom, left:right]
        return Frame(np.ascontiguousarray(img), time.perf_counter(), regiao)

    def parar(self) -> None:
        if self._control is not None:
            try:
                self._control.stop()
            except Exception:
                pass
            self._control = None
