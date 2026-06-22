"""Fábrica de capturador: escolhe o backend e cai para o próximo automaticamente.

Ordem do `auto`: DXGI (bettercam, só Python <3.13) -> WGC (Windows Graphics Capture,
pega DX11/DX12/OpenGL e roda no 3.13) -> mss (GDI, fallback Python puro).

Para clientes com WDA_EXCLUDEFROMCAPTURE (ex.: Tibia oficial com BattlEye), use
backend: tibia_arquivo e configure tibia_screenshots + hotkey_screenshot no config.yaml.

O mss NÃO captura surfaces aceleradas por GPU (DX12 vem preto); por isso o WGC entra
antes dele no `auto`. Cada nível é tentado com try/except e cai para o próximo.
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
    tibia_screenshots: str = "",
    hotkey_screenshot: str = "ctrl+p",
    fps_alvo: float = 3.0,
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
            emitir(f"DXGI/bettercam indisponível ({e})")
            if backend == "bettercam":
                emitir("caindo para o próximo backend...")

    if backend in ("auto", "wgc"):
        try:
            from bot.captura.wgc import CapturadorWGC

            cap = CapturadorWGC(monitor=monitor)
            cap.iniciar()
            emitir("Captura: backend WGC (Windows Graphics Capture) ativo — pega DX12/OpenGL")
            return cap
        except Exception as e:  # ImportError, sem display, ou sem frame
            emitir(f"WGC indisponível ({e}); usando mss")

    if backend in ("auto", "mss"):
        cap = CapturadorMSS(monitor=monitor)
        cap.iniciar()
        emitir("Captura: backend mss (Python puro/GDI) ativo — NÃO captura DX12 (vem preto)")
        return cap

    if backend == "tibia_arquivo":
        try:
            from bot.captura.tibia_arquivo import CapturadorTibiaArquivo

            cap = CapturadorTibiaArquivo(
                pasta=tibia_screenshots,
                hotkey=hotkey_screenshot,
                fps=fps_alvo,
            )
            cap.iniciar()
            emitir(
                f"Captura: backend tibia_arquivo ativo "
                f"(hotkey '{hotkey_screenshot}', pasta: {cap._pasta})"
            )
            return cap
        except Exception as e:
            raise RuntimeError(f"Backend tibia_arquivo falhou: {e}") from e

    raise RuntimeError(
        f"Backend '{backend}' desconhecido. Use: auto | bettercam | wgc | mss | tibia_arquivo"
    )
