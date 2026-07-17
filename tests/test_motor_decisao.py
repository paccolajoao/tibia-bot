"""Testes do motor de decisão e das camadas de cura — OFFLINE, com contextos sintéticos."""

from __future__ import annotations

from bot.configuracao import Config
from bot.contexto import Contexto
from bot.decisao.comportamentos.camada_cura import cooldowns_cura, montar_camadas_cura
from bot.decisao.cooldown import GerenciadorCooldown
from bot.decisao.motor import MotorDecisao
from bot.decisao.tipos import TipoAcao
from bot.visao.tipos import LeituraBarra


def _ctx(hp=None, mana=None, confianca=1.0):
    cfg = Config()
    ctx = Contexto(config=cfg)
    if hp is not None:
        ctx.hp = LeituraBarra(hp, confianca)
    if mana is not None:
        ctx.mana = LeituraBarra(mana, confianca)
    return ctx, cfg


def _motor(cfg):
    return MotorDecisao(
        montar_camadas_cura(cfg.cura, cfg.visao.confianca_minima),
        GerenciadorCooldown(cooldowns_cura(cfg.cura)),
    )


def test_hp_critico_dispara_cura_forte():
    ctx, cfg = _ctx(hp=30)  # <= hp_critico (35): camada de maior prioridade
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.PRESSIONAR_TECLA
    assert dec.tecla == cfg.cura.tecla_cura_forte


def test_hp_amarelo_dispara_pocao_vida():
    ctx, cfg = _ctx(hp=55)  # entre hp_critico (35) e hp_pocao_vida (65)
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.tecla == cfg.cura.tecla_pocao_vida


def test_hp_baixo_dispara_cura_leve():
    ctx, cfg = _ctx(hp=75)  # entre hp_pocao_vida (65) e hp_baixo (90): só cura leve
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.tecla == cfg.cura.tecla_cura_leve


def test_hp_cheio_nao_age():
    ctx, cfg = _ctx(hp=95, mana=95)  # acima de hp_baixo (90) e mana_baixa (40)
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.NENHUMA


def test_mana_baixa_dispara_pocao():
    ctx, cfg = _ctx(hp=95, mana=20)  # HP ok (acima do seguro 70) -> bebe mana
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.tecla == cfg.cura.tecla_pocao_mana


def test_confianca_baixa_e_ignorada():
    ctx, cfg = _ctx(hp=10, confianca=0.2)
    dec = _motor(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.NENHUMA


def test_cooldown_suprime_repeticao():
    # HP 75 isola a camada cura_leve (cd 2.0s); sem outra camada disparando,
    # o cooldown suprime a repetição até expirar.
    ctx, cfg = _ctx(hp=75)
    m = _motor(cfg)
    d1 = m.decidir(ctx, 0.0)
    assert d1.acao == TipoAcao.PRESSIONAR_TECLA
    assert d1.tecla == cfg.cura.tecla_cura_leve
    m.confirmar_acao(d1, 0.0)

    d2 = m.decidir(ctx, 0.1)  # dentro do cooldown (2.0s)
    assert d2.acao == TipoAcao.NENHUMA
    assert "cooldown" in d2.motivo.lower()

    d3 = m.decidir(ctx, 2.5)  # fora do cooldown
    assert d3.acao == TipoAcao.PRESSIONAR_TECLA
    assert d3.tecla == cfg.cura.tecla_cura_leve
