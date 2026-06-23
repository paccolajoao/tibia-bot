"""Input de teclado e mouse via `pydirectinput` (SendInput).

SendInput funciona em jogos DirectX onde o pyautogui (APIs antigas) falha.
Cada ação (tecla ou clique) é cercada por jitter humano (antes/depois).
"""

from __future__ import annotations

from bot.entrada.atrasos import atraso_humano


class EntradaDirectInput:
    def __init__(
        self,
        atraso_pre_ms: tuple[int, int] = (40, 90),
        atraso_pos_ms: tuple[int, int] = (30, 70),
    ):
        import pydirectinput

        pydirectinput.PAUSE = 0  # gerenciamos os atrasos nós mesmos
        pydirectinput.FAILSAFE = False
        self._pdi = pydirectinput
        self._pre = atraso_pre_ms
        self._pos = atraso_pos_ms

    def pressionar_tecla(self, tecla: str) -> None:
        atraso_humano(self._pre)
        self._pdi.press(tecla)
        atraso_humano(self._pos)

    def clicar(self, x: int, y: int) -> None:
        atraso_humano(self._pre)
        self._pdi.moveTo(x, y)
        self._pdi.click()
        atraso_humano(self._pos)

    def clicar_direito(self, x: int, y: int) -> None:
        atraso_humano(self._pre)
        self._pdi.moveTo(x, y)
        self._pdi.click(button="right")
        atraso_humano(self._pos)

    def arrastar(self, x1: int, y1: int, x2: int, y2: int) -> None:
        atraso_humano(self._pre)
        self._pdi.moveTo(x1, y1)
        self._pdi.mouseDown()
        self._pdi.moveTo(x2, y2)  # arrasta segurando o botão
        self._pdi.mouseUp()
        atraso_humano(self._pos)
