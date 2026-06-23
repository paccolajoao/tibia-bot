"""Entrada simulada (no-op) — registra teclas em vez de enviá-las.

Útil para testes headless e para rodar o painel sem mexer no jogo.
"""

from __future__ import annotations

from collections.abc import Callable


class EntradaSimulada:
    def __init__(self, log: Callable[[str], None] | None = None):
        self.teclas: list[str] = []
        self.cliques: list[tuple[int, int]] = []
        self.arrastos: list[tuple[int, int, int, int]] = []
        self._log = log or (lambda _msg: None)

    def pressionar_tecla(self, tecla: str) -> None:
        self.teclas.append(tecla)
        self._log(f"[SIMULADO] pressionaria {tecla}")

    def clicar(self, x: int, y: int) -> None:
        self.cliques.append((x, y))
        self._log(f"[SIMULADO] clicaria em ({x}, {y})")

    def arrastar(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.arrastos.append((x1, y1, x2, y2))
        self._log(f"[SIMULADO] arrastaria ({x1}, {y1}) -> ({x2}, {y2})")
