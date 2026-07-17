"""Testes do jitter humano e do atraso de reação — OFFLINE, sem sleeps reais."""

from __future__ import annotations

import time

import pytest

from bot.entrada.atrasos import atraso_humano, eh_cura_critica, faixa_atraso_reacao

# Formatos reais de `dados` produzidos pelo bot (ver decisao/comportamentos/*.py e
# CLAUDE.md — mapeamento recurso -> estatística).
DADOS_CURA_FORTE = {"recurso": "hp", "nivel": "critico"}
DADOS_POCAO_VIDA = {"recurso": "pocao_vida"}
DADOS_CURA_LEVE = {"recurso": "hp", "nivel": "baixo"}
DADOS_POCAO_MANA = {"recurso": "mana"}
DADOS_ALVO = {"recurso": "alvo"}
DADOS_SAQUE = {"recurso": "saque"}
DADOS_CAVEBOT = {"recurso": "cavebot"}
DADOS_MAGIA_ATAQUE = {"recurso": "magia_ataque"}
DADOS_COMIDA = {"recurso": "comida"}


@pytest.mark.parametrize(
    "dados,esperado",
    [
        (DADOS_CURA_FORTE, True),
        (DADOS_POCAO_VIDA, True),
        (DADOS_CURA_LEVE, False),
        (DADOS_POCAO_MANA, False),
        (DADOS_ALVO, False),
        (DADOS_SAQUE, False),
        (DADOS_CAVEBOT, False),
        (DADOS_MAGIA_ATAQUE, False),
        (DADOS_COMIDA, False),
        ({}, False),
    ],
)
def test_eh_cura_critica(dados, esperado):
    assert eh_cura_critica(dados) is esperado


@pytest.mark.parametrize("dados", [DADOS_CURA_FORTE, DADOS_POCAO_VIDA])
def test_faixa_atraso_reacao_usa_faixa_critica(dados):
    assert faixa_atraso_reacao(dados, (100, 1500), (0, 50)) == (0, 50)


@pytest.mark.parametrize(
    "dados", [DADOS_CURA_LEVE, DADOS_POCAO_MANA, DADOS_ALVO, DADOS_SAQUE, DADOS_CAVEBOT, DADOS_MAGIA_ATAQUE, DADOS_COMIDA, {}]
)
def test_faixa_atraso_reacao_usa_faixa_normal(dados):
    assert faixa_atraso_reacao(dados, (100, 1500), (0, 50)) == (100, 1500)


def test_atraso_humano_no_op_quando_maximo_zero(monkeypatch):
    chamado = False

    def _sleep_falso(_s):
        nonlocal chamado
        chamado = True

    monkeypatch.setattr(time, "sleep", _sleep_falso)
    atraso_humano((0, 0))
    assert not chamado


def test_atraso_humano_dorme_dentro_da_faixa(monkeypatch):
    duracoes = []
    monkeypatch.setattr(time, "sleep", lambda s: duracoes.append(s))
    atraso_humano((100, 200))
    assert len(duracoes) == 1
    assert 0.1 <= duracoes[0] <= 0.2
