"""Testes da detecção de marca no minimapa — OFFLINE, sintético."""

from __future__ import annotations

import numpy as np

from bot.visao.marca_minimapa import detectar_marca


def _icone(lado: int = 11) -> np.ndarray:
    """Ícone BGR distinto (cruz branca sobre fundo vermelho) — bom p/ matchTemplate."""
    img = np.zeros((lado, lado, 3), dtype=np.uint8)
    img[:] = (0, 0, 200)
    img[lado // 2, :] = (255, 255, 255)
    img[:, lado // 2] = (255, 255, 255)
    return img


def _crop_com_marca(dx: int, dy: int, lado: int = 61, ic: int = 11) -> np.ndarray:
    """Crop de minimapa (fundo cinza) com o ícone centrado em (centro+dx, centro+dy)."""
    crop = np.full((lado, lado, 3), 90, dtype=np.uint8)
    cx, cy = lado // 2 + dx, lado // 2 + dy
    icone = _icone(ic)
    x0, y0 = cx - ic // 2, cy - ic // 2
    crop[y0:y0 + ic, x0:x0 + ic] = icone
    return crop


def test_acha_marca_no_offset_esperado():
    crop = _crop_com_marca(12, -8)
    achou, offset, score = detectar_marca(crop, _icone(), threshold=0.7)
    assert achou is True
    assert offset == (12, -8)
    assert score >= 0.7


def test_marca_no_centro_offset_zero():
    crop = _crop_com_marca(0, 0)
    achou, offset, _ = detectar_marca(crop, _icone(), threshold=0.7)
    assert achou is True
    assert offset == (0, 0)


def test_marca_ausente_nao_encontra():
    # crop uniforme, sem o ícone -> não encontra (mas devolve score p/ calibração).
    crop = np.full((61, 61, 3), 90, dtype=np.uint8)
    achou, offset, score = detectar_marca(crop, _icone(), threshold=0.7)
    assert achou is False
    assert offset is None
    assert isinstance(score, float)


def test_score_sempre_devolvido_abaixo_do_threshold():
    crop = _crop_com_marca(5, 5)
    # threshold impossível -> não "encontra", mas o score real (alto) é devolvido.
    achou, offset, score = detectar_marca(crop, _icone(), threshold=1.01)
    assert achou is False
    assert offset is None
    assert score > 0.7


def test_entradas_invalidas():
    assert detectar_marca(None, _icone()) == (False, None, 0.0)
    assert detectar_marca(_crop_com_marca(0, 0), None) == (False, None, 0.0)
    vazio = np.zeros((0, 0, 3), dtype=np.uint8)
    assert detectar_marca(vazio, _icone()) == (False, None, 0.0)


def test_respeita_mascara_alfa():
    # template BGRA: borda transparente. O match deve ignorar o fundo transparente e
    # achar o ícone mesmo com o fundo do crop diferente da borda do template.
    ic = 11
    bgra = np.zeros((ic, ic, 4), dtype=np.uint8)
    bgra[..., :3] = _icone(ic)
    bgra[..., 3] = 255           # tudo opaco...
    bgra[0, :, 3] = 0            # ...menos a 1ª linha (transparente)
    bgra[-1, :, 3] = 0           # ...e a última
    crop = _crop_com_marca(6, 4, ic=ic)
    achou, offset, _ = detectar_marca(crop, bgra, threshold=0.7)
    assert achou is True
    assert offset == (6, 4)
