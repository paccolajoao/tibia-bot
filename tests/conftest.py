"""Fixtures de teste: geram imagens sintéticas de barras (sem precisar do jogo)."""

from __future__ import annotations

import numpy as np
import pytest


def _fazer_barra(
    percentual: float,
    largura: int = 120,
    altura: int = 14,
    cor_preench: tuple[int, int, int] = (0, 0, 200),  # BGR vermelho (HP)
    cor_vazio: tuple[int, int, int] = (15, 15, 15),
    invertido: bool = False,
) -> np.ndarray:
    """Gera uma barra sintética. `invertido` enche da direita p/ esquerda (mana)."""
    img = np.empty((altura, largura, 3), np.uint8)
    img[:, :] = cor_vazio
    n = int(round(largura * percentual / 100.0))
    if n > 0:
        if invertido:
            img[:, largura - n :] = cor_preench  # ancorada à direita
        else:
            img[:, :n] = cor_preench
    return img


def _por_numeros(img: np.ndarray) -> np.ndarray:
    """Desenha uma faixa horizontal de 'números' (branco, baixa saturação) no meio.

    Simula o texto "165/170" sobreposto à barra: o branco tem S baixo, então um
    classificador ingênuo o trataria como vazio. Cobre ~40% da altura, centralizado.
    """
    img = img.copy()
    altura, largura = img.shape[:2]
    y0 = int(altura * 0.3)
    y1 = int(altura * 0.7)
    # "dígitos" espaçados pela largura toda (branco)
    for x in range(int(largura * 0.2), int(largura * 0.8), 8):
        img[y0:y1, x : x + 3] = (255, 255, 255)
    return img


@pytest.fixture
def fazer_barra():
    return _fazer_barra


@pytest.fixture
def fazer_barra_invertida():
    def _f(percentual: float, **kw) -> np.ndarray:
        return _fazer_barra(percentual, invertido=True, **kw)

    return _f


@pytest.fixture
def fazer_barra_com_numeros():
    def _f(percentual: float, invertido: bool = False, **kw) -> np.ndarray:
        return _por_numeros(_fazer_barra(percentual, invertido=invertido, **kw))

    return _f


@pytest.fixture
def fazer_barra_ocluida():
    def _f(percentual: float, largura: int = 120, altura: int = 14) -> np.ndarray:
        img = _fazer_barra(percentual, largura=largura, altura=altura)
        a, b = int(largura * 0.15), int(largura * 0.30)
        img[:, a:b] = (15, 15, 15)  # buraco escuro no meio do preenchido (algo cobrindo)
        return img

    return _f
