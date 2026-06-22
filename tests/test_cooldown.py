"""Testes do GerenciadorCooldown."""

from __future__ import annotations

from bot.decisao.cooldown import GerenciadorCooldown


def test_cooldown_basico():
    g = GerenciadorCooldown({"f5": 1.0})
    assert g.pode_disparar("f5", 0.0)
    g.registrar("f5", 0.0)
    assert not g.pode_disparar("f5", 0.5)
    assert g.pode_disparar("f5", 1.0)


def test_restante():
    g = GerenciadorCooldown({"f5": 2.0})
    g.registrar("f5", 10.0)
    assert abs(g.restante("f5", 10.5) - 1.5) < 1e-6
    assert g.restante("f5", 99.0) == 0.0


def test_tecla_sem_cooldown_sempre_dispara():
    g = GerenciadorCooldown({})
    assert g.pode_disparar("x", 0.0)
    g.registrar("x", 0.0)
    assert g.pode_disparar("x", 0.0)
