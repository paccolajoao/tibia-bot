"""Detecção de itens por template matching — offline, imagens sintéticas."""

from __future__ import annotations

import cv2
import numpy as np

from bot.visao.inventario import detectar_itens


def _icone_texturizado(w=16, h=16, marcador=(0, 255, 0)) -> np.ndarray:
    """Ícone com textura (gradiente + marcador). matchTemplate degenera em cor sólida
    (variância zero) — itens reais têm textura, então o template de teste também tem."""
    icon = np.zeros((h, w, 3), np.uint8)
    icon[:, :, 0] = np.linspace(0, 255, w, dtype=np.uint8)[None, :]  # B: gradiente horizontal
    icon[:, :, 2] = np.linspace(255, 0, h, dtype=np.uint8)[:, None]  # R: gradiente vertical
    icon[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4] = marcador        # marcador central
    return icon


def _inventario_com_item(pos=(40, 20), tam=(16, 16)):
    """Fundo cinza (backpack) com um 'item' texturizado numa posição conhecida."""
    img = np.full((80, 120, 3), 40, np.uint8)  # cinza escuro
    x, y = pos
    w, h = tam
    template = _icone_texturizado(w, h)
    img[y : y + h, x : x + w] = template
    centro = (x + w // 2, y + h // 2)
    return img, template.copy(), centro


def test_encontra_item_no_centro_certo():
    img, template, centro = _inventario_com_item()
    achados = detectar_itens(img, (0, 0, 120, 80), [("rune", template)], threshold=0.9)
    assert len(achados) == 1
    assert achados[0].nome == "rune"
    assert abs(achados[0].ponto[0] - centro[0]) <= 2
    assert abs(achados[0].ponto[1] - centro[1]) <= 2


def test_item_ausente_nao_e_detectado():
    img, _template, _ = _inventario_com_item()
    # template texturizado, mas com padrão diferente do que está no inventário
    outro = _icone_texturizado(marcador=(255, 0, 255))[::-1]  # espelhado: não casa
    achados = detectar_itens(img, (0, 0, 120, 80), [("erva", outro)], threshold=0.95)
    assert achados == []


def test_threshold_filtra_match_fraco():
    img, template, _ = _inventario_com_item()
    # threshold impossível -> nada passa
    achados = detectar_itens(img, (0, 0, 120, 80), [("rune", template)], threshold=1.01)
    assert achados == []


def test_template_maior_que_regiao_e_ignorado():
    img, _t, _ = _inventario_com_item()
    grande = np.zeros((200, 200, 3), np.uint8)
    achados = detectar_itens(img, (0, 0, 120, 80), [("x", grande)], threshold=0.5)
    assert achados == []


def test_encontra_item_em_escala_diferente():
    """Ícone no inventário é 1.5x maior que o template cadastrado -> multi-escala acha."""
    base = _icone_texturizado(16, 16)
    grande = cv2.resize(base, (24, 24), interpolation=cv2.INTER_LINEAR)  # item renderizado maior
    img = np.full((80, 120, 3), 40, np.uint8)
    img[20:44, 40:64] = grande
    achados = detectar_itens(img, (0, 0, 120, 80), [("rune", base)], threshold=0.9)
    assert len(achados) == 1
    assert achados[0].nome == "rune"
    assert abs(achados[0].ponto[0] - (40 + 12)) <= 3
    assert abs(achados[0].ponto[1] - (20 + 12)) <= 3


def _gradiente(w=16, h=16) -> np.ndarray:
    """Ícone totalmente texturizado (gradientes nos 3 canais, sem bloco sólido)."""
    icon = np.zeros((h, w, 3), np.uint8)
    icon[:, :, 0] = np.linspace(0, 255, w, dtype=np.uint8)[None, :]
    icon[:, :, 1] = np.linspace(255, 0, w, dtype=np.uint8)[None, :]
    icon[:, :, 2] = np.linspace(0, 255, h, dtype=np.uint8)[:, None]
    return icon


def test_template_com_alfa_usa_mascara_ignorando_fundo():
    """Template transparente (só o miolo opaco e texturizado) casa mesmo com fundo diferente."""
    grad = _gradiente(16, 16)
    # template BGRA: opaco só no miolo 8x8 (que é texturizado), transparente nas bordas
    bgra = np.zeros((16, 16, 4), np.uint8)
    bgra[:, :, :3] = grad
    bgra[4:12, 4:12, 3] = 255  # alfa: só o miolo conta no match
    # inventário: miolo idêntico ao do template, mas bordas com ruído (sem máscara não casaria)
    img = np.full((80, 120, 3), 40, np.uint8)
    ruido = np.random.RandomState(0).randint(0, 255, (16, 16, 3), dtype=np.uint8)
    img[20:36, 40:56] = ruido
    img[24:32, 44:52] = grad[4:12, 4:12]  # miolo idêntico no lugar certo
    achados = detectar_itens(img, (0, 0, 120, 80), [("rune", bgra)], threshold=0.9)
    assert len(achados) == 1
    assert achados[0].nome == "rune"
