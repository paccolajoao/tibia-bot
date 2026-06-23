"""Detecção de MOVIMENTO no minimapa (não de posição absoluta).

O cavebot clica pontos no minimapa e deixa o Tibia pathfindar cada trecho; a
"chegada" é detectada quando o minimapa PARA DE ROLAR. Em vez de ler a posição
mundial do player (caro e frágil num pixel-bot), comparamos dois crops
consecutivos do minimapa: enquanto o personagem anda o minimapa rola e o diff é
alto; quando ele para, o diff cai a ~zero.

O marcador central do player (a setinha/ponto branco que pisca no centro) é
mascarado para não gerar falso "movimento" quando o resto está parado.

Função pura `(np.ndarray, np.ndarray, float) -> (movendo, score)` => testável offline.
"""

from __future__ import annotations

import cv2
import numpy as np

# Lado (em px) do quadrado central mascarado sobre o marcador do player.
LADO_MASCARA_CENTRO = 6


def minimapa_movendo(
    crop_atual: np.ndarray,
    crop_anterior: np.ndarray | None,
    limiar: float = 2.0,
) -> tuple[bool, float]:
    """Compara dois crops do minimapa e diz se está rolando (player andando).

    `score` é o diff absoluto médio por pixel (0..255) ignorando o centro. Acima
    de `limiar` => movendo. Sem crop anterior (1ª leitura) ou shapes diferentes
    (região recém-mudada) => não-movendo, score 0.
    """
    if crop_anterior is None or crop_atual.shape != crop_anterior.shape:
        return (False, 0.0)
    if crop_atual.size == 0:
        return (False, 0.0)

    a = cv2.cvtColor(crop_atual, cv2.COLOR_BGR2GRAY) if crop_atual.ndim == 3 else crop_atual
    b = cv2.cvtColor(crop_anterior, cv2.COLOR_BGR2GRAY) if crop_anterior.ndim == 3 else crop_anterior

    diff = cv2.absdiff(a, b)

    # mascara o marcador do player no centro (zera o diff lá)
    h, w = diff.shape[:2]
    cy, cx = h // 2, w // 2
    r = LADO_MASCARA_CENTRO // 2
    diff[max(0, cy - r):cy + r + 1, max(0, cx - r):cx + r + 1] = 0

    score = float(diff.mean())
    return (score > limiar, score)
