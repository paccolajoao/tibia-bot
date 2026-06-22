"""Interface da camada de input."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EntradaBase(Protocol):
    def pressionar_tecla(self, tecla: str) -> None: ...

    def clicar(self, x: int, y: int) -> None: ...
