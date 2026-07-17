"""Testes da detecção da battle list — OFFLINE, com imagens sintéticas (numpy)."""

from __future__ import annotations

import numpy as np

from bot.visao.lista_batalha import detectar_criaturas

VERDE = (0, 200, 0)  # BGR — mini HP-bar saudável
VERMELHO = (0, 0, 200)  # BGR — realce do alvo atual


def _img(h: int = 100, w: int = 200) -> np.ndarray:
    img = np.empty((h, w, 3), np.uint8)
    img[:] = (15, 15, 15)  # fundo escuro da lista
    return img


def _bar(img, y0, y1, x0=5, x1=130, cor=VERDE) -> None:
    img[y0:y1, x0:x1] = cor


def _regiao(img) -> tuple[int, int, int, int]:
    h, w = img.shape[:2]
    return (0, 0, w, h)


def test_lista_vazia_zero_criaturas():
    img = _img()
    det = detectar_criaturas(img, _regiao(img))
    assert det.n_criaturas == 0
    assert det.alvo_atual is False
    assert det.centro_primeira is None
    assert det.confianca == 1.0


def test_uma_criatura():
    img = _img()
    _bar(img, 10, 16)
    det = detectar_criaturas(img, _regiao(img))
    assert det.n_criaturas == 1
    assert det.centro_primeira is not None
    cx, cy = det.centro_primeira
    assert 10 <= cy <= 16  # centro vertical dentro da barra
    assert 5 <= cx <= 130


def test_varias_criaturas_grupos_separados():
    img = _img()
    _bar(img, 10, 16)
    _bar(img, 40, 46)
    _bar(img, 70, 76)
    det = detectar_criaturas(img, _regiao(img))
    assert det.n_criaturas == 3
    # centro da PRIMEIRA entrada
    assert det.centro_primeira is not None
    assert 10 <= det.centro_primeira[1] <= 16


def test_alvo_atual_detecta_realce_vermelho():
    img = _img()
    _bar(img, 10, 16)  # criatura
    img[30:60, 5:130] = VERMELHO  # bloco de realce vermelho (entrada atacada)
    det = detectar_criaturas(img, _regiao(img))
    assert det.alvo_atual is True
    assert det.n_criaturas >= 1


def test_sem_alvo_quando_so_verde():
    img = _img()
    _bar(img, 10, 16)
    _bar(img, 40, 46)
    det = detectar_criaturas(img, _regiao(img))
    assert det.alvo_atual is False


def test_confianca_baixa_quando_lista_coberta():
    img = _img()
    img[:, :] = VERDE  # tudo saturado -> algo cobrindo a lista
    det = detectar_criaturas(img, _regiao(img))
    assert det.confianca < 0.6


# ----------------------------- vida_primeira (watchdog "sem dano" do Alvo) -----------------------------
# `vida_primeira` é lida sobre a largura TOTAL da região (não só o span do _bar() de conveniência
# usado acima) — por isso os testes abaixo desenham a partir de x0=0, coerente com a suposição já
# embutida em `linha_bar` (uma entrada de verdade satura boa parte da largura da lista).


def test_vida_primeira_cheia_quando_bar_preenche_toda_largura():
    img = _img()
    _bar(img, 10, 16, x0=0, x1=200)  # preenche a largura toda -> ~100%
    det = detectar_criaturas(img, _regiao(img))
    assert det.vida_primeira is not None
    assert det.vida_primeira.percentual >= 95


def test_vida_primeira_parcial_quando_bar_preenche_metade():
    img = _img()
    _bar(img, 10, 16, x0=0, x1=100)  # metade da largura -> ~50%
    det = detectar_criaturas(img, _regiao(img))
    assert det.vida_primeira is not None
    assert 35 <= det.vida_primeira.percentual <= 65


def test_vida_primeira_none_sem_criaturas():
    img = _img()
    det = detectar_criaturas(img, _regiao(img))
    assert det.vida_primeira is None


def test_vida_primeira_usa_so_a_primeira_entrada():
    img = _img()
    _bar(img, 10, 16, x0=0, x1=200)  # 1ª criatura: cheia
    # 2ª criatura: baixa (mas >= largura_min_frac=0.3 p/ ainda contar como entrada)
    _bar(img, 40, 46, x0=0, x1=70)
    det = detectar_criaturas(img, _regiao(img))
    assert det.n_criaturas == 2
    assert det.vida_primeira is not None
    assert det.vida_primeira.percentual >= 95
