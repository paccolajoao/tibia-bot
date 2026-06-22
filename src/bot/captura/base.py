"""Interface da camada de captura + tipo Frame.

Backends concretos (DXGI/bettercam, mss) implementam `CapturadorBase`. O resto
do bot só conhece esta interface, então trocar de backend é trivial.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

# (left, top, right, bottom) em pixels absolutos do desktop
Regiao = tuple[int, int, int, int]


@dataclass
class Frame:
    imagem: np.ndarray  # HxWx3, BGR, uint8
    ts: float  # time.perf_counter() da captura
    regiao: Regiao | None = None  # região absoluta que este frame representa (None = tela cheia)


@runtime_checkable
class CapturadorBase(Protocol):
    @property
    def nome_backend(self) -> str: ...

    def iniciar(self) -> None: ...

    def capturar(self, regiao: Regiao | None = None) -> Frame | None: ...

    def parar(self) -> None: ...
