"""Testes da detecção de movimento do minimapa — OFFLINE, sintético."""

from __future__ import annotations

import numpy as np

from bot.visao.minimap import minimapa_movendo


def _crop(valor: int) -> np.ndarray:
    return np.full((40, 40, 3), valor, dtype=np.uint8)


def test_sem_crop_anterior_nao_move():
    movendo, score = minimapa_movendo(_crop(100), None)
    assert movendo is False
    assert score == 0.0


def test_crops_iguais_nao_movem():
    a = _crop(120)
    movendo, score = minimapa_movendo(a, a.copy())
    assert movendo is False
    assert score == 0.0


def test_crops_diferentes_movem():
    a = _crop(40)
    b = _crop(200)
    movendo, score = minimapa_movendo(a, b, limiar=2.0)
    assert movendo is True
    assert score > 2.0


def test_shapes_diferentes_nao_movem():
    a = np.zeros((40, 40, 3), dtype=np.uint8)
    b = np.zeros((30, 30, 3), dtype=np.uint8)
    movendo, _ = minimapa_movendo(a, b)
    assert movendo is False


def test_marcador_central_e_mascarado():
    # só o centro difere (marcador do player piscando): NÃO deve contar como movimento.
    a = _crop(100)
    b = _crop(100)
    cy, cx = 20, 20
    b[cy - 1:cy + 2, cx - 1:cx + 2] = 255
    movendo, score = minimapa_movendo(a, b, limiar=2.0)
    assert movendo is False
    assert score == 0.0
