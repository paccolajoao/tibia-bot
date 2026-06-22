"""Testes da leitura de barras — rodam OFFLINE contra imagens sintéticas."""

from __future__ import annotations

import pytest

from bot.visao.barra_recursos import ler_percentual_barra

REGIAO = (0, 0, 120, 14)


@pytest.mark.parametrize("pct", [0, 25, 50, 75, 100])
def test_percentual_aproximado(fazer_barra, pct):
    img = fazer_barra(pct)
    leitura = ler_percentual_barra(img, REGIAO)
    assert abs(leitura.percentual - pct) <= 6


def test_confianca_alta_em_barra_limpa(fazer_barra):
    leitura = ler_percentual_barra(fazer_barra(50), REGIAO)
    assert leitura.confianca >= 0.9


def test_confianca_baixa_com_oclusao(fazer_barra_ocluida):
    leitura = ler_percentual_barra(fazer_barra_ocluida(50), REGIAO)
    assert leitura.confianca < 0.8


def test_barra_mana_azul(fazer_barra):
    # mana é azul (BGR 200,0,0); o classificador usa V+S, não Hue, então funciona igual
    leitura = ler_percentual_barra(fazer_barra(60, cor_preench=(200, 0, 0)), REGIAO)
    assert abs(leitura.percentual - 60) <= 6


def test_regiao_vazia_nao_quebra(fazer_barra):
    leitura = ler_percentual_barra(fazer_barra(50), (0, 0, 0, 0))
    assert leitura.percentual == 0.0
    assert leitura.confianca == 0.0
