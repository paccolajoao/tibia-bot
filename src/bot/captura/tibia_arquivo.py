"""Capturador via screenshot interno do Tibia (arquivo PNG no disco).

O Tibia usa SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE), que instrui o SO
a mascarar o conteúdo da janela para TODA captura externa: mss, WGC, DXGI e até
PrintScreen do Windows. Só o processo do Tibia consegue fotografar seu próprio
conteúdo — exatamente o que a hotkey de screenshot interna faz.

Solução: este backend envia a hotkey de screenshot periodicamente numa thread de
fundo e armazena o PNG mais recente. `capturar()` retorna o último frame sem
bloquear o loop do bot. Taxa típica: 3 FPS — suficiente para auto-heal/targeting.

Configure em config.yaml:
  captura:
    backend: tibia_arquivo
    tibia_screenshots: ""          # vazio = auto-detecta; ou caminho completo
    hotkey_screenshot: ctrl+p     # mesma hotkey de Options > Interface > Screenshot
"""

from __future__ import annotations

import os
import pathlib
import threading
import time

import cv2
import numpy as np

from bot.captura.base import Frame, Regiao

# Pastas candidatas — testadas na ordem
_CANDIDATOS: list[str] = [
    os.path.expandvars(r"%APPDATA%\Tibia\packages\Tibia\screenshots"),
    os.path.expanduser(r"~/Documents/Tibia/screenshots"),
    os.path.expandvars(r"%LOCALAPPDATA%\Tibia\packages\Tibia\screenshots"),
    os.path.expandvars(r"%APPDATA%\Tibia\screenshots"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Tibia\screenshots"),
    os.path.expandvars(r"%ProgramFiles%\Tibia\screenshots"),
]


def detectar_pasta_screenshots() -> pathlib.Path | None:
    """Retorna a 1ª pasta de screenshots do Tibia encontrada no disco, ou None."""
    for c in _CANDIDATOS:
        p = pathlib.Path(c)
        if p.is_dir():
            return p
    return None


def _hotkey_send(hotkey: str) -> None:
    """Envia hotkey global via keyboard (suporta combos como ctrl+p)."""
    try:
        import keyboard

        keyboard.send(hotkey)
    except Exception:
        pass


def _arquivo_mais_novo(pasta: pathlib.Path, t_min: float) -> pathlib.Path | None:
    """Retorna o arquivo PNG/BMP mais recente na pasta com mtime >= t_min."""
    try:
        candidatos: list[tuple[float, pathlib.Path]] = []
        for ext in ("*.png", "*.bmp", "*.PNG", "*.BMP"):
            for f in pasta.glob(ext):
                try:
                    mtime = f.stat().st_mtime
                    if mtime >= t_min:
                        candidatos.append((mtime, f))
                except OSError:
                    pass
        if candidatos:
            candidatos.sort(reverse=True)
            return candidatos[0][1]
    except Exception:
        pass
    return None


class CapturadorTibiaArquivo:
    """Backend de captura via screenshot interno do Tibia (arquivo PNG).

    Thread de fundo envia a hotkey periodicamente e armazena o frame em
    `self._ultimo`. `capturar()` é não-bloqueante (retorna o último frame).
    """

    nome_backend = "tibia_arquivo"

    def __init__(
        self,
        pasta: str = "",
        hotkey: str = "ctrl+p",
        fps: float = 3.0,
        apagar_apos_ler: bool = True,
        timeout_primeiro_frame_s: float = 12.0,
    ):
        self._pasta: pathlib.Path | None = pathlib.Path(pasta) if pasta else None
        self._hotkey = hotkey
        self._intervalo = 1.0 / max(0.5, fps)
        self._apagar = apagar_apos_ler
        self._timeout = timeout_primeiro_frame_s

        self._lock = threading.Lock()
        self._ultimo: np.ndarray | None = None
        self._ultimo_ts: float = 0.0
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._pasta is None:
            self._pasta = detectar_pasta_screenshots()
        if self._pasta is None or not self._pasta.is_dir():
            raise RuntimeError(
                "Pasta de screenshots do Tibia não encontrada.\n"
                "  1. Tire uma screenshot no Tibia (hotkey configurada em Options > Interface)\n"
                "     e veja em qual pasta o arquivo apareceu.\n"
                "  2. Configure 'captura.tibia_screenshots' no config.yaml com esse caminho.\n"
                "  3. Configure 'captura.hotkey_screenshot' com a mesma hotkey."
            )
        self._parar.clear()
        self._thread = threading.Thread(
            target=self._loop, name="TibiaArquivo", daemon=True
        )
        self._thread.start()

        # aguarda o 1º frame; se não chegar, lança erro útil
        prazo = time.perf_counter() + self._timeout
        while time.perf_counter() < prazo:
            with self._lock:
                if self._ultimo is not None:
                    return
            time.sleep(0.1)
        self._parar.set()
        raise RuntimeError(
            f"Nenhum screenshot recebido em {self._timeout:.0f}s.\n"
            f"  • Hotkey configurada: '{self._hotkey}' — confira em Options > Interface do Tibia.\n"
            f"  • Pasta monitorada: {self._pasta}\n"
            "  • O Tibia precisa estar em foco para receber a hotkey."
        )

    def capturar(self, regiao: Regiao | None = None) -> Frame | None:
        with self._lock:
            img = self._ultimo
            ts = self._ultimo_ts
        if img is None:
            return None
        if regiao is not None:
            left, top, right, bottom = regiao
            img = img[top:bottom, left:right]
        return Frame(np.ascontiguousarray(img), ts, regiao)

    def parar(self) -> None:
        self._parar.set()

    # ------------------------------------------------------------------ loop
    def _loop(self) -> None:
        while not self._parar.is_set():
            t0 = time.perf_counter()
            self._disparar_e_ler()
            dt = time.perf_counter() - t0
            self._parar.wait(max(0.0, self._intervalo - dt))

    def _disparar_e_ler(self) -> None:
        """Envia a hotkey e aguarda o arquivo aparecer na pasta (até 3 s)."""
        t_antes = time.time() - 0.3  # margem para resolução do relógio do FS
        _hotkey_send(self._hotkey)

        prazo = time.perf_counter() + 3.0
        while time.perf_counter() < prazo:
            time.sleep(0.05)
            arquivo = _arquivo_mais_novo(self._pasta, t_antes)
            if arquivo is None:
                continue
            time.sleep(0.03)  # espera o Tibia terminar de escrever
            try:
                img = cv2.imread(str(arquivo))
            except Exception:
                img = None
            if img is None:
                continue
            with self._lock:
                self._ultimo = img
                self._ultimo_ts = time.perf_counter()
            if self._apagar:
                try:
                    arquivo.unlink(missing_ok=True)
                except Exception:
                    pass
            return
