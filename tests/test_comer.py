"""Testes do comportamento Comer — OFFLINE, dirigindo contexto.ts."""

from __future__ import annotations

from bot.configuracao import Config
from bot.contexto import Contexto
from bot.decisao.comportamentos.comer import Comer
from bot.decisao.tipos import TipoAcao


def _ctx(ts: float):
    cfg = Config()
    ctx = Contexto(config=cfg)
    ctx.ts = ts
    return ctx, cfg


def test_come_no_primeiro_tick_e_respeita_intervalo():
    ctx, cfg = _ctx(ts=1000.0)
    comer = Comer(cfg.comer)  # intervalo_s padrão = 120

    d1 = comer.avaliar(ctx)
    assert d1 is not None
    assert d1.acao == TipoAcao.PRESSIONAR_TECLA
    assert d1.tecla == cfg.comer.tecla
    assert d1.dados["recurso"] == "comida"

    # antes do intervalo -> não come
    ctx.ts = 1000.0 + cfg.comer.intervalo_s - 1
    assert comer.avaliar(ctx) is None

    # passado o intervalo -> come de novo
    ctx.ts = 1000.0 + cfg.comer.intervalo_s + 0.1
    d2 = comer.avaliar(ctx)
    assert d2 is not None
    assert d2.acao == TipoAcao.PRESSIONAR_TECLA


def test_inativo_nunca_come():
    ctx, cfg = _ctx(ts=5000.0)
    cfg.comer.ativo = False
    comer = Comer(cfg.comer)
    assert comer.avaliar(ctx) is None
