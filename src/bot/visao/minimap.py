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


def diferenca_minimapa(
    crop_a: np.ndarray,
    crop_b: np.ndarray | None,
) -> float:
    """Diff absoluto médio por pixel (0..255) entre dois crops do minimapa,
    ignorando o marcador central do player.

    Base compartilhada por `minimapa_movendo` (crops consecutivos → detecta rolagem)
    e pela validação de troca de andar do cavebot (crop atual × referência pré-ação →
    detecta que o mapa mudou de forma persistente). Sem crop de comparação (1ª leitura),
    shapes diferentes (região recém-mudada) ou crop vazio => 0.0.
    """
    if crop_b is None or crop_a.shape != crop_b.shape or crop_a.size == 0:
        return 0.0

    a = cv2.cvtColor(crop_a, cv2.COLOR_BGR2GRAY) if crop_a.ndim == 3 else crop_a
    b = cv2.cvtColor(crop_b, cv2.COLOR_BGR2GRAY) if crop_b.ndim == 3 else crop_b

    diff = cv2.absdiff(a, b)

    # mascara o marcador do player no centro (zera o diff lá)
    h, w = diff.shape[:2]
    cy, cx = h // 2, w // 2
    r = LADO_MASCARA_CENTRO // 2
    diff[max(0, cy - r):cy + r + 1, max(0, cx - r):cx + r + 1] = 0

    return float(diff.mean())


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
    score = diferenca_minimapa(crop_atual, crop_anterior)
    return (score > limiar, score)
