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


def eh_cura_critica(dados: dict) -> bool:
    """As 2 camadas de cura de maior prioridade (cura_forte, poção de vida).

    Usado para isentar o atraso de reação: não vale a pena "reagir devagar" a um
    pânico de HP (ver decisao/comportamentos/camada_cura.py e configuracao.py:
    EntradaConfig.atraso_reacao_critico_ms).
    """
    recurso = dados.get("recurso")
    if recurso == "pocao_vida":
        return True
    return recurso == "hp" and dados.get("nivel") == "critico"


def faixa_atraso_reacao(
    dados: dict, normal_ms: tuple[int, int], critico_ms: tuple[int, int]
) -> tuple[int, int]:
    """Escolhe a faixa de atraso de reação a aplicar antes de uma ação executada."""
    return critico_ms if eh_cura_critica(dados) else normal_ms
