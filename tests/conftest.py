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
) -> np.ndarray:
    img = np.empty((altura, largura, 3), np.uint8)
    img[:, :] = cor_vazio
    n = int(round(largura * percentual / 100.0))
    if n > 0:
        img[:, :n] = cor_preench
    return img


@pytest.fixture
def fazer_barra():
    return _fazer_barra


@pytest.fixture
def fazer_barra_ocluida():
    def _f(percentual: float, largura: int = 120, altura: int = 14) -> np.ndarray:
        img = _fazer_barra(percentual, largura=largura, altura=altura)
        a, b = int(largura * 0.15), int(largura * 0.30)
        img[:, a:b] = (15, 15, 15)  # buraco escuro no meio do preenchido (algo cobrindo)
        return img

    return _f
