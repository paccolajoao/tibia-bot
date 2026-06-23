"""Testes do comportamento UsarMana — OFFLINE, dirigindo contexto.mana."""

from __future__ import annotations

from bot.configuracao import Config
from bot.contexto import Contexto
from bot.decisao.comportamentos.usar_mana import UsarMana
from bot.decisao.tipos import TipoAcao
from bot.visao.tipos import LeituraBarra


def _ctx(mana_pct: float, conf: float = 1.0):
    cfg = Config()
    ctx = Contexto(config=cfg)
    ctx.mana = LeituraBarra(mana_pct, conf)
    return ctx, cfg


def test_casta_com_mana_acima_do_limiar():
    ctx, cfg = _ctx(mana_pct=96.0)  # default mana_alto=95
    d = UsarMana(cfg.usar_mana).avaliar(ctx)
    assert d is not None
    assert d.acao == TipoAcao.PRESSIONAR_TECLA
    assert d.tecla == cfg.usar_mana.tecla
    assert d.dados["recurso"] == "mana_uso"  # NÃO "mana" (não conta como poção)


def test_perfil_legado_mana_alto_100_ainda_dispara():
    """Mana cheia raramente lê 100%; um perfil salvo com mana_alto=100 deve casta com ~98%."""
    ctx, cfg = _ctx(mana_pct=98.0)
    cfg.usar_mana.mana_alto = 100.0  # valor antigo "inatingível"
    d = UsarMana(cfg.usar_mana).avaliar(ctx)
    assert d is not None  # limiar efetivo cai p/ 97 -> dispara


def test_histerese_segura_gastando_ate_mana_alvo():
    ctx, cfg = _ctx(mana_pct=96.0)  # mana_alto=95, mana_alvo=80
    uso = UsarMana(cfg.usar_mana)
    assert uso.avaliar(ctx) is not None  # ativa

    ctx.mana = LeituraBarra(85.0, 1.0)  # entre alvo e alto -> continua gastando
    assert uso.avaliar(ctx) is not None

    ctx.mana = LeituraBarra(79.0, 1.0)  # abaixo do alvo -> para
    assert uso.avaliar(ctx) is None

    ctx.mana = LeituraBarra(90.0, 1.0)  # subiu mas < mana_alto -> NÃO reativa (histerese)
    assert uso.avaliar(ctx) is None


def test_abaixo_do_limiar_nao_casta():
    ctx, cfg = _ctx(mana_pct=90.0)  # < mana_alto (95) e nunca ativou
    assert UsarMana(cfg.usar_mana).avaliar(ctx) is None


def test_confianca_baixa_ignora():
    ctx, cfg = _ctx(mana_pct=99.0, conf=0.3)  # abaixo de confianca_minima (0.6)
    assert UsarMana(cfg.usar_mana).avaliar(ctx) is None
