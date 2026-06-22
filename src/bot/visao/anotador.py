"""Desenha um overlay no frame para o dashboard: o usuário VÊ o que o bot vê.

Marca as regiões de HP/Mana, o % lido e a última decisão. A cor da caixa fica
laranja quando a confiança da leitura está baixa (sinaliza leitura suspeita).
"""

from __future__ import annotations

import cv2
import numpy as np

from bot.captura.base import Regiao
from bot.visao.tipos import LeituraBarra

_FONTE = cv2.FONT_HERSHEY_SIMPLEX
_VERDE = (0, 255, 0)
_LARANJA = (0, 165, 255)
_CIANO = (255, 255, 0)


def desenhar_overlay(
    imagem: np.ndarray,
    leituras: list[tuple[str, Regiao, LeituraBarra]],
    decisao_texto: str | None = None,
) -> np.ndarray:
    """`leituras`: lista de (rótulo, regiao_em_coords_da_imagem, LeituraBarra)."""
    saida = imagem.copy()
    for rotulo, (left, top, right, bottom), leitura in leituras:
        cor = _VERDE if leitura.confianca >= 0.6 else _LARANJA
        cv2.rectangle(saida, (left, top), (right, bottom), cor, 1)
        cv2.putText(
            saida,
            f"{rotulo}: {leitura.percentual:.0f}%",
            (left, max(10, top - 4)),
            _FONTE,
            0.4,
            cor,
            1,
            cv2.LINE_AA,
        )
    if decisao_texto:
        cv2.putText(
            saida,
            decisao_texto,
            (4, saida.shape[0] - 6),
            _FONTE,
            0.45,
            _CIANO,
            1,
            cv2.LINE_AA,
        )
    return saida
