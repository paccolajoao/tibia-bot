"""Cooldown por tecla: evita spam de hotkey e respeita o cooldown do jogo."""

from __future__ import annotations


class GerenciadorCooldown:
    def __init__(self, cooldowns_s: dict[str, float]):
        self._cooldowns = cooldowns_s
        self._ultimo: dict[str, float] = {}

    def pode_disparar(self, tecla: str, agora: float) -> bool:
        cd = self._cooldowns.get(tecla, 0.0)
        ultimo = self._ultimo.get(tecla)
        return ultimo is None or (agora - ultimo) >= cd

    def registrar(self, tecla: str, agora: float) -> None:
        self._ultimo[tecla] = agora

    def restante(self, tecla: str, agora: float) -> float:
        cd = self._cooldowns.get(tecla, 0.0)
        ultimo = self._ultimo.get(tecla)
        if ultimo is None:
            return 0.0
        return max(0.0, cd - (agora - ultimo))
