"""Detecção de itens no inventário/backpack por template matching (OpenCV).

Dado um conjunto de templates (ícones de itens recortados no portal) e a região do
inventário, varre por `cv2.matchTemplate` e devolve o centro de cada item encontrado
acima de um threshold. Usado pelo comportamento de Drop para arrastar o item ao chão.

Os pontos retornados são em COORDENADAS DA REGIÃO (o chamador soma o offset da
região e, se for OBS, aplica o mapeamento canvas->desktop).

Função pura `(np.ndarray, regiao, templates, threshold) -> list[ItemDetectado]`
=> testável offline.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import cv2
import numpy as np

from bot.captura.base import Regiao


@dataclass
class ItemDetectado:
    nome: str
    ponto: tuple[int, int]  # centro do match, em coords da região do inventário
    score: float


def decodificar_template(template_b64: str) -> np.ndarray | None:
    """Decodifica um PNG/JPEG em base64 (vindo do portal) para BGR ndarray. None se inválido."""
    try:
        dados = base64.b64decode(template_b64)
        arr = np.frombuffer(dados, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # BGR, descarta alfa
        return img if img is not None and img.size > 0 else None
    except Exception:
        return None


def detectar_itens(
    imagem: np.ndarray,
    regiao: Regiao,
    templates: list[tuple[str, np.ndarray]],
    threshold: float = 0.85,
) -> list[ItemDetectado]:
    """Acha o melhor match de cada template dentro da região. Um item por template.

    `templates`: lista de (nome, imagem_BGR). Templates maiores que a ROI são ignorados.
    """
    left, top, right, bottom = regiao
    roi = imagem[top:bottom, left:right]
    if roi.size == 0:
        return []

    encontrados: list[ItemDetectado] = []
    rh, rw = roi.shape[:2]
    for nome, tpl in templates:
        if tpl is None or tpl.size == 0:
            continue
        th, tw = tpl.shape[:2]
        if th > rh or tw > rw:
            continue  # template maior que a região -> matchTemplate quebraria
        res = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
        _min, maxval, _minloc, maxloc = cv2.minMaxLoc(res)
        if maxval >= threshold:
            cx = int(maxloc[0] + tw / 2)
            cy = int(maxloc[1] + th / 2)
            encontrados.append(ItemDetectado(nome, (cx, cy), float(maxval)))
    # mais confiantes primeiro (o comportamento dropa o melhor primeiro)
    encontrados.sort(key=lambda i: i.score, reverse=True)
    return encontrados
