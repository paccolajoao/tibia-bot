"""Testes do comportamento Saque (Quick Loot) — OFFLINE, contextos sintéticos.

O Saque só gerencia a CADÊNCIA dos presses; a detecção de morte é feita pelo loop e
exposta em `ctx.estado_comportamentos["saque_morte_ts"]`. Aqui simulamos esse sinal.
"""

from __future__ import annotations

from bot.configuracao import Config
from bot.contexto import Contexto
from bot.decisao.comportamentos.saque import Saque
from bot.decisao.tipos import TipoAcao


def _ctx(ts, morte_ts=None):
    cfg = Config()
    ctx = Contexto(config=cfg)
    ctx.ts = ts
    if morte_ts is not None:
        ctx.estado_comportamentos["saque_morte_ts"] = morte_ts
    return ctx, cfg


def test_sem_morte_nao_saqueia():
    ctx, cfg = _ctx(ts=100.0)
    s = Saque(cfg.saque)
    assert s.avaliar(ctx) is None


def test_morte_dispara_quick_loot():
    ctx, cfg = _ctx(ts=100.0, morte_ts=100.0)
    s = Saque(cfg.saque)
    dec = s.avaliar(ctx)
    assert dec is not None
    assert dec.acao == TipoAcao.PRESSIONAR_TECLA
    assert dec.tecla == cfg.saque.tecla
    assert dec.dados["recurso"] == "saque"


def test_presses_repetem_na_janela_e_param_depois():
    ctx, cfg = _ctx(ts=0.0, morte_ts=0.0)
    s = Saque(cfg.saque)
    assert s.avaliar(ctx) is not None  # 1º press imediato

    ctx.ts = cfg.saque.intervalo_press_s * 0.5  # dentro do intervalo -> sem press
    assert s.avaliar(ctx) is None

    ctx.ts = cfg.saque.intervalo_press_s + 0.01  # passou o intervalo, ainda na janela
    assert s.avaliar(ctx) is not None

    ctx.ts = cfg.saque.janela_s + 1.0  # após a janela -> para
    assert s.avaliar(ctx) is None


def test_nova_morte_reabre_a_janela():
    ctx, cfg = _ctx(ts=0.0, morte_ts=0.0)
    s = Saque(cfg.saque)
    assert s.avaliar(ctx) is not None

    # janela expira
    ctx.ts = cfg.saque.janela_s + 5.0
    assert s.avaliar(ctx) is None

    # nova morte (morte_ts diferente) -> reabre e aperta de novo
    ctx.estado_comportamentos["saque_morte_ts"] = ctx.ts
    assert s.avaliar(ctx) is not None


def test_inativo_nunca_saqueia():
    ctx, cfg = _ctx(ts=0.0, morte_ts=0.0)
    cfg.saque.ativo = False
    s = Saque(cfg.saque)
    assert s.avaliar(ctx) is None
