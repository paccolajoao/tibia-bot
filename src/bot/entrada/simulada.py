"""Entrada simulada (no-op) — registra teclas em vez de enviá-las.

Útil para testes headless e para rodar o painel sem mexer no jogo.
"""

from __future__ import annotations

from collections.abc import Callable


class EntradaSimulada:
    def __init__(self, log: Callable[[str], None] | None = None):
        self.teclas: list[str] = []
        self.cliques: list[tuple[int, int]] = []
        self._log = log or (lambda _msg: None)

    def pressionar_tecla(self, tecla: str) -> None:
        self.teclas.append(tecla)
        self._log(f"[SIMULADO] pressionaria {tecla}")

    def clicar(self, x: int, y: int) -> None:
        self.cliques.append((x, y))
        self._log(f"[SIMULADO] clicaria em ({x}, {y})")
