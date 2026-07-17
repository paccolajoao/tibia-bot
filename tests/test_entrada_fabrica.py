"""Testes da fábrica de entrada — OFFLINE, sem hardware."""

from __future__ import annotations

import pytest

from bot.configuracao import ArduinoConfig
from bot.entrada.fabrica import criar_entrada
from bot.entrada.teclado_directinput import EntradaDirectInput


def test_criar_entrada_directinput():
    entrada = criar_entrada("directinput")
    assert isinstance(entrada, EntradaDirectInput)


def test_criar_entrada_arduino_porta_inexistente_levanta():
    # Porta COM inexistente falha ao abrir em qualquer máquina, sem precisar de hardware.
    with pytest.raises(RuntimeError, match="Backend arduino falhou"):
        criar_entrada("arduino", arduino=ArduinoConfig(porta="COM999", timeout_s=0.05))


def test_criar_entrada_backend_desconhecido_levanta():
    with pytest.raises(RuntimeError, match="directinput \\| arduino"):
        criar_entrada("bogus")
