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


@pytest.mark.parametrize("pct", [0, 25, 50, 75, 100])
def test_barra_invertida_le_correto(fazer_barra_invertida, pct):
    # mana enche da direita->esquerda: sem invertido=True leria errado
    img = fazer_barra_invertida(pct, cor_preench=(200, 0, 0))
    leitura = ler_percentual_barra(img, REGIAO, invertido=True)
    assert abs(leitura.percentual - pct) <= 6


def test_barra_invertida_sem_flag_le_errado(fazer_barra_invertida):
    # prova que a direção importa: 30% ancorado à direita, lido como normal,
    # cai no ramo "começa vazia" e infla p/ ~100% — bem longe dos 30% reais.
    img = fazer_barra_invertida(30, cor_preench=(200, 0, 0))
    leitura = ler_percentual_barra(img, REGIAO, invertido=False)
    assert abs(leitura.percentual - 30) > 40  # leitura claramente errada sem o flag


@pytest.mark.parametrize("pct", [25, 50, 75, 97])
def test_numeros_sobre_a_barra_nao_quebram(fazer_barra_com_numeros, pct):
    # texto branco (baixa saturação) sobreposto não pode derrubar o %
    img = fazer_barra_com_numeros(pct)
    leitura = ler_percentual_barra(img, REGIAO)
    assert abs(leitura.percentual - pct) <= 8
    assert leitura.confianca >= 0.9  # uma transição só -> confiança alta


def test_numeros_em_barra_invertida(fazer_barra_com_numeros):
    img = fazer_barra_com_numeros(87, invertido=True, cor_preench=(200, 0, 0))
    leitura = ler_percentual_barra(img, REGIAO, invertido=True)
    assert abs(leitura.percentual - 87) <= 8
