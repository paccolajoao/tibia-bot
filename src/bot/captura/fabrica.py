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
    obs_device_index: int = 0,
    obs_device_nome: str = "OBS Virtual Camera",
    obs_largura: int = 1920,
    obs_altura: int = 1080,
) -> CapturadorBase:
    emitir = log or (lambda _msg: None)

    if backend == "obs":
        try:
            from bot.captura.obs_virtualcam import CapturadorOBS

            cap = CapturadorOBS(
                indice=obs_device_index,
                nome_device=obs_device_nome,
                largura=obs_largura,
                altura=obs_altura,
            )
            cap.iniciar()
            frame = cap.capturar(None)
            dims = f"{frame.imagem.shape[1]}x{frame.imagem.shape[0]}" if frame else "?"
            emitir(
                f"Captura: backend OBS Virtual Camera ativo (device índice {cap._indice}, {dims}) "
                "— frame do canvas do OBS"
            )
            return cap
        except Exception as e:
            raise RuntimeError(
                f"Backend obs falhou: {e}. Abra o OBS, monte uma cena com captura do "
                "Tibia e clique em 'Start Virtual Camera'."
            ) from e

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
        f"Backend '{backend}' desconhecido. Use: auto | bettercam | wgc | mss | obs | tibia_arquivo"
    )
