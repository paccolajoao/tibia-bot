"""Atrasos com jitter humano — evita timing perfeitamente periódico/idêntico.

Prudência (input mais natural e que respeita o ritmo do jogo), não evasão.
"""

from __future__ import annotations

import random
import time


def atraso_humano(faixa_ms: tuple[int, int]) -> None:
    minimo, maximo = faixa_ms
    if maximo <= 0:
        return
    time.sleep(random.uniform(minimo, maximo) / 1000.0)
