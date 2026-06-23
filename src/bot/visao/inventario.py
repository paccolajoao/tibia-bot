"""Detecção de itens no inventário/backpack por template matching (OpenCV).

Dado um conjunto de templates (ícones de itens recortados no portal) e a região do
inventário, varre por `cv2.matchTemplate` e devolve o centro de cada item encontrado
acima de um threshold. Usado pelo comportamento de Drop para arrastar o item ao chão.

Os pontos retornados são em COORDENADAS DA REGIÃO (o chamador soma o offset da
região e, se for OBS, aplica o mapeamento canvas->desktop).

O matchTemplate é SENSÍVEL À ESCALA: um ícone de wiki/PNG externo dificilmente tem
o mesmo tamanho do ícone renderizado no cliente. Por isso varremos várias escalas
do template e ficamos com o melhor match. Imagens com canal alfa (PNG/GIF
transparentes) usam o alfa como MÁSCARA, ignorando o fundo transparente no match.

Função pura `(np.ndarray, regiao, templates, threshold) -> list[ItemDetectado]`
=> testável offline.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import cv2
import numpy as np

from bot.captura.base import Regiao

# Escalas testadas por template (relativas ao tamanho original). Cobre ícones
# externos maiores/menores que o render do cliente; 1.0 sempre incluso.
ESCALAS = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5)


@dataclass
class ItemDetectado:
    nome: str
    ponto: tuple[int, int]  # centro do match, em coords da região do inventário
    score: float


def decodificar_template(template_b64: str) -> np.ndarray | None:
    """Decodifica um PNG/GIF/JPEG base64 (do portal) para ndarray. None se inválido.

    Usa IMREAD_UNCHANGED para PRESERVAR o canal alfa (BGRA) quando houver — assim
    `detectar_itens` pode usá-lo como máscara. Imagens sem alfa voltam como BGR.
    """
    try:
        dados = base64.b64decode(template_b64)
        arr = np.frombuffer(dados, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        return img if img is not None and img.size > 0 else None
    except Exception:
        return None


def _normalizar_template(tpl: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
    """Devolve (BGR 3-canais, máscara|None) a partir de um template em qualquer formato.

    A máscara (quando o template tem alfa) marca os pixels opacos do ícone, para o
    match ignorar o fundo transparente das imagens externas.
    """
    if tpl.ndim == 2:  # grayscale
        return cv2.cvtColor(tpl, cv2.COLOR_GRAY2BGR), None
    canais = tpl.shape[2]
    if canais == 4:  # BGRA
        bgr = tpl[:, :, :3]
        alfa = tpl[:, :, 3]
        mascara = np.where(alfa > 0, 255, 0).astype(np.uint8)
        return bgr, mascara
    if canais == 3:  # BGR
        return tpl, None
    return cv2.cvtColor(tpl, cv2.COLOR_GRAY2BGR), None  # 1 canal "achatado"


def _melhor_match(
    roi: np.ndarray, bgr: np.ndarray, mascara: np.ndarray | None
) -> tuple[float, tuple[int, int], int, int]:
    """Melhor (score, canto_sup_esq, largura, altura) do template na ROI, varrendo escalas."""
    rh, rw = roi.shape[:2]
    th0, tw0 = bgr.shape[:2]
    melhor_score = -1.0
    melhor_loc = (0, 0)
    melhor_wh = (tw0, th0)
    for s in ESCALAS:
        tw = int(round(tw0 * s))
        th = int(round(th0 * s))
        if tw < 4 or th < 4 or tw > rw or th > rh:
            continue  # pequeno demais p/ casar ou maior que a ROI nessa escala
        interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR
        tpl = cv2.resize(bgr, (tw, th), interpolation=interp)
        msk = cv2.resize(mascara, (tw, th), interpolation=cv2.INTER_NEAREST) if mascara is not None else None
        res = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED, mask=msk)
        # zero-variância (template/máscara degenerados) -> NaN/inf; trata como 0.
        res = np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0)
        _min, maxval, _minloc, maxloc = cv2.minMaxLoc(res)
        if maxval > melhor_score:
            melhor_score = float(maxval)
            melhor_loc = maxloc
            melhor_wh = (tw, th)
    return melhor_score, melhor_loc, melhor_wh[0], melhor_wh[1]


def detectar_itens(
    imagem: np.ndarray,
    regiao: Regiao,
    templates: list[tuple[str, np.ndarray]],
    threshold: float = 0.85,
) -> list[ItemDetectado]:
    """Acha o melhor match de cada template dentro da região. Um item por template.

    `templates`: lista de (nome, imagem). A imagem pode ser BGR ou BGRA (alfa vira
    máscara). O match é multi-escala; escalas que excedem a ROI são ignoradas.
    """
    left, top, right, bottom = regiao
    roi = imagem[top:bottom, left:right]
    if roi.size == 0:
        return []

    encontrados: list[ItemDetectado] = []
    for nome, tpl in templates:
        if tpl is None or tpl.size == 0:
            continue
        bgr, mascara = _normalizar_template(tpl)
        score, loc, tw, th = _melhor_match(roi, bgr, mascara)
        if score >= threshold:
            cx = int(loc[0] + tw / 2)
            cy = int(loc[1] + th / 2)
            encontrados.append(ItemDetectado(nome, (cx, cy), score))
    # mais confiantes primeiro (o comportamento dropa o melhor primeiro)
    encontrados.sort(key=lambda i: i.score, reverse=True)
    return encontrados
