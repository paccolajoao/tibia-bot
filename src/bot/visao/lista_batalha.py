"""Detecção de criaturas na battle list por amostragem de pixels.

Trabalha em COORDENADAS DA IMAGEM (o chamador converte de/para absolutas).
Cada entrada de criatura na battle list tem um mini HP-bar horizontal colorido e
saturado. A heurística aqui:

  - classifica pixels "saturados" por S+V (mesmo critério V+S de `barra_recursos`);
  - acha linhas onde um trecho horizontal saturado largo o bastante existe (o bar);
  - agrupa linhas-bar consecutivas em ENTRADAS -> conta criaturas;
  - detecta `alvo_atual` pela presença de realce VERMELHO (a entrada atacada ganha
    moldura/realce vermelho no client).

É um primeiro slice — robusto o bastante para ligar/atacar, upgradeável a template
matching depois. Função pura `(np.ndarray, regiao, ...) -> DeteccaoCriaturas`.
"""

from __future__ import annotations

import cv2
import numpy as np

from bot.captura.base import Regiao
from bot.visao.tipos import DeteccaoCriaturas


def detectar_criaturas(
    imagem: np.ndarray,
    regiao: Regiao,
    s_min: int = 60,
    v_min: int = 60,
    largura_min_frac: float = 0.3,
    realce_min_frac: float = 0.015,
) -> DeteccaoCriaturas:
    left, top, right, bottom = regiao
    roi = imagem[top:bottom, left:right]
    if roi.size == 0 or roi.shape[0] < 2 or roi.shape[1] < 2:
        return DeteccaoCriaturas(0, False, 0.0, None)

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0].astype(int)
    s = hsv[:, :, 1].astype(int)
    v = hsv[:, :, 2].astype(int)
    saturado = (s >= s_min) & (v >= v_min)

    # linha é "bar" quando uma fração grande dela está saturada (o mini HP-bar)
    frac_linha = saturado.mean(axis=1)
    linha_bar = frac_linha >= largura_min_frac
    grupos = _agrupar_runs(linha_bar)
    n = len(grupos)

    centro = _centro_primeira(saturado, grupos, roi.shape[1])
    # Verifica o realce por grupo individual (limiar menor: bordas têm poucos pixels)
    alvo = any(
        _tem_realce_vermelho(h[y0 : y1 + 1], saturado[y0 : y1 + 1], 0.005)
        for y0, y1 in grupos
    )
    confianca = _confianca(float(saturado.mean()))
    return DeteccaoCriaturas(n, alvo, confianca, centro)


def _agrupar_runs(mascara: np.ndarray) -> list[tuple[int, int]]:
    """Runs contíguos de True em `mascara` -> lista de (inicio, fim) inclusivos."""
    grupos: list[tuple[int, int]] = []
    inicio: int | None = None
    for i, ligado in enumerate(mascara):
        if ligado and inicio is None:
            inicio = i
        elif not ligado and inicio is not None:
            grupos.append((inicio, i - 1))
            inicio = None
    if inicio is not None:
        grupos.append((inicio, len(mascara) - 1))
    return grupos


def _centro_primeira(
    saturado: np.ndarray, grupos: list[tuple[int, int]], largura: int
) -> tuple[int, int] | None:
    if not grupos:
        return None
    y0, y1 = grupos[0]
    faixa = saturado[y0 : y1 + 1]
    cols = faixa.any(axis=0)
    xs = np.flatnonzero(cols)
    cx = int((xs[0] + xs[-1]) // 2) if xs.size else largura // 2
    cy = (y0 + y1) // 2
    return (cx, cy)


def _tem_realce_vermelho(h: np.ndarray, saturado: np.ndarray, realce_min_frac: float) -> bool:
    """A entrada atacada tem realce vermelho — hue perto de 0/180, saturado.

    Range alargado (<=20 / >=160) p/ capturar laranja-vermelho que o cliente Tibia
    usa como indicador de alvo ativo; limiar mantido p/ não falso-positivo.
    """
    vermelho = ((h <= 20) | (h >= 160)) & saturado
    return bool(vermelho.mean() >= realce_min_frac)


def _confianca(cobertura: float) -> float:
    """Só cobertura saturada QUASE total (tooltip/overlay colorido cobrindo a lista)
    derruba a confiança. Uma battle list cheia de criaturas satura bastante de forma
    legítima, então o limiar é alto (0.85) p/ não descartar listas com vários bichos.
    """
    if cobertura <= 0.85:
        return 1.0
    return max(0.0, 1.0 - (cobertura - 0.85) * 3.0)
