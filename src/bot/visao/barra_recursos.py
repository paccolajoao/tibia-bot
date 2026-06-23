"""Leitura de % de uma barra (HP/Mana) por amostragem de pixels.

Trabalha em COORDENADAS DA IMAGEM (o chamador converte de coords absolutas).
Classifica preenchido vs vazio por HSV usando V (brilho) + S (saturação) — NÃO o
matiz (Hue) — então sobrevive à mudança de cor do HP (verde -> vermelho) e serve
à mana azul com o mesmo critério.

A classificação é feita por COLUNA usando toda a altura da barra (não uma única
scanline): uma coluna conta como preenchida se uma fração mínima dos seus pixels
estiver preenchida. Isso a torna robusta aos NÚMEROS sobrepostos na barra (ex.:
"165/170"), cujo texto branco tem saturação baixa — a cor da barra acima/abaixo do
dígito mantém a coluna preenchida.

`invertido=True` trata barras que enchem da DIREITA->ESQUERDA (a mana do Tibia
esvazia da esquerda p/ direita): basta espelhar o array de colunas antes de aplicar
a mesma lógica "contíguo a partir da borda".

Função pura `(np.ndarray, regiao, v_min, s_min, invertido) -> LeituraBarra`
=> testável offline.
"""

from __future__ import annotations

import cv2
import numpy as np

from bot.captura.base import Regiao
from bot.visao.tipos import LeituraBarra

# Fração mínima de pixels preenchidos numa coluna para considerá-la "cheia".
# Baixa o suficiente para sobreviver a números/ícones sobre a barra, alta o
# suficiente para ignorar 1-2 pixels espúrios de borda.
FRACAO_COLUNA = 0.25


def ler_percentual_barra(
    imagem: np.ndarray,
    regiao: Regiao,
    v_min: int = 60,
    s_min: int = 50,
    invertido: bool = False,
) -> LeituraBarra:
    left, top, right, bottom = regiao
    roi = imagem[top:bottom, left:right]
    if roi.size == 0 or roi.shape[1] < 2:
        return LeituraBarra(0.0, 0.0)

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1].astype(int)
    v = hsv[:, :, 2].astype(int)
    mascara = (v >= v_min) & (s >= s_min)  # 2D: preenchido por pixel

    # Por coluna: cheia se uma fração mínima da altura estiver preenchida.
    fracao = mascara.mean(axis=0)  # fração preenchida de cada coluna
    preenchido = fracao >= FRACAO_COLUNA
    if invertido:
        preenchido = preenchido[::-1]  # barra ancorada à direita -> espelha

    total = int(preenchido.size)
    n_preench = int(preenchido.sum())

    # Após o espelhamento, o algoritmo sempre assume preenchimento a partir da
    # esquerda. O percentual é a posição do primeiro pixel vazio após a região
    # preenchida inicial. Usar o ÚLTIMO preenchido seria sensível a pixels
    # espúrios de borda (frame da UI) que inflariam p/ 100%.
    if n_preench == 0:
        percentual = 0.0
    elif n_preench == total:
        percentual = 100.0
    elif preenchido[0]:
        # caso normal: barra começa preenchida; primeiro vazio = fim do preenchimento
        idx_corte = int(np.flatnonzero(~preenchido)[0])
        percentual = idx_corte / total * 100.0
    else:
        # barra começa vazia (raro, p.ex. região calibrada inclui área antes da barra)
        idx_ultimo = int(np.max(np.flatnonzero(preenchido)))
        percentual = (idx_ultimo + 1) / total * 100.0

    confianca = _confianca(preenchido, n_preench, total)
    return LeituraBarra(percentual, confianca)


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
