"""Testes do motor de decisão e do AutoCura — OFFLINE, com contextos sintéticos."""

from __future__ import annotations

from bot.configuracao import Config
from bot.contexto import Contexto
from bot.decisao.comportamentos.auto_cura import AutoCura
from bot.decisao.cooldown import GerenciadorCooldown
from bot.decisao.motor import MotorDecisao
from bot.decisao.tipos import TipoAcao
from bot.visao.tipos import LeituraBarra


def _ctx(hp=None, mana=None, confianca=1.0):
    cfg = Config()
    ctx = Contexto(config=cfg)
    if hp is not None:
        ctx.hp = LeituraBarra(hp, 64, 0, confianca)
    if mana is not None:
        ctx.mana = LeituraBarra(mana, 64, 0, confianca)
    return ctx, cfg


def _motor(cfg):
    return MotorDecisao(
        [AutoCura(cfg.cura, cfg.visao.confianca_minima)],
        GerenciadorCooldown(cfg.cura.cooldown_s),
    )


def test_hp_critico_dispara_cura_forte():
    ctx, cfg = _ctx(hp=30)
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.PRESSIONAR_TECLA
    assert dec.tecla == cfg.cura.tecla_cura_forte


def test_hp_baixo_dispara_cura_leve():
    ctx, cfg = _ctx(hp=55)
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.tecla == cfg.cura.tecla_cura_leve


def test_hp_cheio_nao_age():
    ctx, cfg = _ctx(hp=95, mana=95)
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.NENHUMA


def test_mana_baixa_dispara_pocao():
    ctx, cfg = _ctx(hp=95, mana=20)
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.tecla == cfg.cura.tecla_pocao_mana


def test_confianca_baixa_e_ignorada():
    ctx, cfg = _ctx(hp=10, confianca=0.2)
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.NENHUMA


def test_cooldown_suprime_repeticao():
    ctx, cfg = _ctx(hp=30)
    m = _motor(cfg)
    d1 = m.decidir(ctx, 0.0)
    assert d1.acao == TipoAcao.PRESSIONAR_TECLA
    m.confirmar_acao(d1, 0.0)

    d2 = m.decidir(ctx, 0.1)  # dentro do cooldown (1.0s)
    assert d2.acao == TipoAcao.NENHUMA
    assert "cooldown" in d2.motivo.lower()

    d3 = m.decidir(ctx, 1.5)  # fora do cooldown
    assert d3.acao == TipoAcao.PRESSIONAR_TECLA
