"""Interface da camada de input."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EntradaBase(Protocol):
    def pressionar_tecla(self, tecla: str) -> None: ...

    def clicar(self, x: int, y: int) -> None: ...

    def clicar_direito(self, x: int, y: int) -> None:
        """Clique com o botão direito em (x, y) — usar escada/alavanca (cavebot)."""
        ...

    def arrastar(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Arrasta (mouse down em (x1,y1), move até (x2,y2), mouse up) — drop de item."""
        ...
