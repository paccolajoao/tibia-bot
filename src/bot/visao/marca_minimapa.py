"""Detecção de uma MARCA nativa do Tibia no minimapa (template matching).

Reaproveita a engine multi-escala do inventário (`cv2.matchTemplate` + máscara alfa)
aplicada ao crop do minimapa: acha o ícone da marca cadastrada e devolve seu OFFSET
em relação ao CENTRO do crop (= posição do personagem, já que o minimapa é sempre
centrado no boneco).

O cavebot usa esse offset para (a) clicar em `centro + offset` e mandar o Tibia andar
até a marca, e (b) detectar a chegada: à medida que o personagem anda, a marca converge
para o centro (offset -> ~0) — quando |offset| fica dentro de um raio, chegou.

Função pura `(crop, template, threshold, escalas) -> (encontrou, offset, score)` =>
testável offline.
"""

from __future__ import annotations

import numpy as np

# Reusa os helpers do inventário (mesma engine de matchTemplate com máscara alfa).
from bot.visao.inventario import _melhor_match, _normalizar_template

# Sweep de escala ESTREITO: a marca é capturada no zoom do próprio minimapa do usuário,
# então varia pouco (só compensa anti-aliasing / erro de recorte). Faixa larga custaria
# CPU à toa e aumentaria falso-positivo.
ESCALAS_MARCA = (0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15)


def detectar_marca(
    crop: np.ndarray | None,
    template: np.ndarray | None,
    threshold: float = 0.7,
    escalas: tuple[float, ...] = ESCALAS_MARCA,
) -> tuple[bool, tuple[int, int] | None, float]:
    """Acha a marca no crop do minimapa.

    Retorna `(encontrou, offset_do_centro, score)`:
    - `offset_do_centro = (dx, dy)` do centro do match ao centro do crop, em px
      (positivo = direita/baixo) — pronto p/ virar clique `relativo_centro`.
    - `encontrou=False` e offset `None` quando `score < threshold` ou entradas inválidas.
    - O `score` real é **sempre** devolvido (mesmo abaixo do threshold), para o portal
      exibir ao vivo e ajudar a calibrar `marca_threshold`.
    """
    if crop is None or crop.size == 0 or template is None or template.size == 0:
        return (False, None, 0.0)
    bgr, mascara = _normalizar_template(template)
    score, loc, tw, th = _melhor_match(crop, bgr, mascara, escalas)
    h, w = crop.shape[:2]
    cx = loc[0] + tw / 2
    cy = loc[1] + th / 2
    offset = (int(round(cx - w / 2)), int(round(cy - h / 2)))
    if score >= threshold:
        return (True, offset, score)
    return (False, None, score)
