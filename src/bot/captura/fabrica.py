"""Fábrica de capturador: tenta DXGI (bettercam) e cai para mss automaticamente.

É aqui que o backend é escolhido e onde o fallback de-risca o Python 3.13.
"""

from __future__ import annotations

from collections.abc import Callable

from bot.captura.base import CapturadorBase
from bot.captura.mss_fallback import CapturadorMSS

Logger = Callable[[str], None]


def criar_capturador(
    backend: str = "auto",
    monitor: int = 0,
    log: Logger | None = None,
) -> CapturadorBase:
    emitir = log or (lambda _msg: None)

    if backend in ("auto", "bettercam"):
        try:
            from bot.captura.dxgi import CapturadorDXGI

            cap = CapturadorDXGI(monitor=monitor)
            cap.iniciar()
            emitir("Captura: backend DXGI (bettercam) ativo")
            return cap
        except Exception as e:  # ImportError ou falha de init
            if backend == "bettercam":
                emitir(f"bettercam indisponível ({e}); usando mss")
            else:
                emitir(f"DXGI indisponível ({e}); usando mss")

    cap = CapturadorMSS(monitor=monitor)
    cap.iniciar()
    emitir("Captura: backend mss (Python puro) ativo")
    return cap
