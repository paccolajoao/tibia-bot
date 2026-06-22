"""Leitura de % de uma barra (HP/Mana) por amostragem de pixels.

Trabalha em COORDENADAS DA IMAGEM (o chamador converte de coords absolutas).
Classifica preenchido vs vazio por HSV usando V (brilho) + S (saturação) — NÃO o
matiz (Hue) — então sobrevive à mudança de cor do HP (verde -> vermelho) e serve
à mana azul com o mesmo critério.

Função pura `(np.ndarray, regiao, v_min, s_min) -> LeituraBarra` => testável offline.
"""

from __future__ import annotations

import cv2
import numpy as np

from bot.captura.base import Regiao
from bot.visao.tipos import LeituraBarra


def ler_percentual_barra(
    imagem: np.ndarray,
    regiao: Regiao,
    v_min: int = 60,
    s_min: int = 50,
    n_amostras: int = 64,
) -> LeituraBarra:
    left, top, right, bottom = regiao
    roi = imagem[top:bottom, left:right]
    if roi.size == 0 or roi.shape[1] < 2:
        return LeituraBarra(0.0, 0, 0, 0.0)

    altura, largura = roi.shape[:2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # scanline horizontal no meio vertical da barra (robusto a bordas de 1px)
    y = altura // 2
    xs = np.unique(np.linspace(0, largura - 1, num=min(n_amostras, largura)).astype(int))
    linha = hsv[y, xs]
    s = linha[:, 1].astype(int)
    v = linha[:, 2].astype(int)
    preenchido = (v >= v_min) & (s >= s_min)

    total = int(preenchido.size)
    n_preench = int(preenchido.sum())

    # percentual = posição da última amostra preenchida (barras esvaziam da direita p/ esquerda)
    if n_preench == 0:
        percentual = 0.0
    else:
        idx_ultimo = int(np.max(np.flatnonzero(preenchido)))
        percentual = (idx_ultimo + 1) / total * 100.0

    confianca = _confianca(preenchido, n_preench, total)
    return LeituraBarra(percentual, total, n_preench, confianca)


def _confianca(preenchido: np.ndarray, n_preench: int, total: int) -> float:
    """Quão limpa foi a transição preenchido->vazio.

    Uma barra saudável tem no máximo 1 transição (cheio à esquerda, vazio à direita).
    Algo cobrindo a barra (tooltip, item flutuando) gera várias transições -> baixa confiança,
    e o motor então ignora a leitura em vez de agir errado.
    """
    if total <= 1:
        return 0.0
    if n_preench == 0 or n_preench == total:
        return 1.0  # totalmente vazia ou cheia: leitura limpa
    transicoes = int(np.sum(preenchido[:-1] != preenchido[1:]))
    if transicoes <= 1:
        return 1.0
    return max(0.0, 1.0 - (transicoes - 1) * 0.25)
