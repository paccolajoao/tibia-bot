"""Picker de retângulo (click-drag) sobre uma captura de tela, via OpenCV.

A imagem é exibida escalada para caber na tela; as coordenadas do mouse são
convertidas de volta para a resolução ORIGINAL antes de retornar.
"""

from __future__ import annotations

import cv2
import numpy as np

from bot.captura.base import Regiao

_FONTE = cv2.FONT_HERSHEY_SIMPLEX
_INSTRUCAO = "Arraste sobre a barra | ENTER=confirmar  R=refazer  ESC=cancelar"


def selecionar_regiao(
    imagem: np.ndarray,
    titulo: str,
    max_w: int = 1600,
    max_h: int = 900,
) -> Regiao | None:
    altura, largura = imagem.shape[:2]
    escala = min(1.0, max_w / largura, max_h / altura)
    if escala < 1.0:
        base = cv2.resize(imagem, (int(largura * escala), int(altura * escala)))
    else:
        base = imagem.copy()

    est = {"ini": None, "fim": None, "arrastando": False}

    def on_mouse(evento, x, y, flags, _param):
        if evento == cv2.EVENT_LBUTTONDOWN:
            est["ini"] = (x, y)
            est["fim"] = (x, y)
            est["arrastando"] = True
        elif evento == cv2.EVENT_MOUSEMOVE and est["arrastando"]:
            est["fim"] = (x, y)
        elif evento == cv2.EVENT_LBUTTONUP:
            est["fim"] = (x, y)
            est["arrastando"] = False

    cv2.namedWindow(titulo, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(titulo, on_mouse)
    try:
        while True:
            quadro = base.copy()
            if est["ini"] and est["fim"]:
                cv2.rectangle(quadro, est["ini"], est["fim"], (0, 255, 0), 2)
            cv2.putText(quadro, _INSTRUCAO, (10, 26), _FONTE, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.imshow(titulo, quadro)
            k = cv2.waitKey(20) & 0xFF
            if k == 13 and est["ini"] and est["fim"]:  # ENTER
                regiao = _normalizar(est["ini"], est["fim"], escala)
                if regiao is not None:
                    return regiao
            elif k in (ord("r"), ord("R")):
                est["ini"] = est["fim"] = None
            elif k == 27:  # ESC
                return None
    finally:
        cv2.destroyWindow(titulo)


def _normalizar(ini, fim, escala: float) -> Regiao | None:
    (x1, y1), (x2, y2) = ini, fim
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    if (right - left) <= 2 or (bottom - top) <= 2:
        return None
    inv = 1.0 / escala
    return (int(left * inv), int(top * inv), int(right * inv), int(bottom * inv))
