"""Testes do comportamento Alvo e sua integração no motor — OFFLINE, sintético."""

from __future__ import annotations

from bot.configuracao import Config
from bot.contexto import Contexto
from bot.decisao.comportamentos.alvo import Alvo
from bot.decisao.comportamentos.auto_cura import AutoCura
from bot.decisao.cooldown import GerenciadorCooldown
from bot.decisao.motor import MotorDecisao
from bot.decisao.tipos import TipoAcao
from bot.visao.tipos import DeteccaoCriaturas, LeituraBarra


def _ctx(criaturas=None, hp=None):
    cfg = Config()
    ctx = Contexto(config=cfg)
    ctx.criaturas = criaturas
    if hp is not None:
        ctx.hp = LeituraBarra(hp, 1.0)
    return ctx, cfg


def _det(n=1, alvo_atual=False, confianca=1.0, ponto=(110, 205)):
    return DeteccaoCriaturas(n, alvo_atual, confianca, (10, 5), ponto_clique=ponto)


def _motor(cfg, comportamentos):
    cooldown = GerenciadorCooldown({**cfg.cura.cooldown_s, **cfg.alvo.cooldown_s})
    return MotorDecisao(comportamentos, cooldown)


def _alvo(cfg):
    return _motor(cfg, [Alvo(cfg.alvo, cfg.visao.confianca_minima)])


def test_clica_quando_criatura_sem_alvo():
    ctx, cfg = _ctx(criaturas=_det(n=2, alvo_atual=False))
    dec = _alvo(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.CLICAR
    assert dec.ponto == (110, 205)
    assert dec.chave_cd == "atacar"


def test_nao_clica_quando_ja_ha_alvo():
    ctx, cfg = _ctx(criaturas=_det(alvo_atual=True))
    dec = _alvo(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.NENHUMA


def test_nao_clica_sem_criaturas():
    ctx, cfg = _ctx(criaturas=_det(n=0))
    dec = _alvo(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.NENHUMA


def test_confianca_baixa_e_ignorada():
    ctx, cfg = _ctx(criaturas=_det(confianca=0.2))
    dec = _alvo(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.NENHUMA


def test_sem_ponto_clique_nao_age():
    ctx, cfg = _ctx(criaturas=_det(ponto=None))
    dec = _alvo(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.NENHUMA


def test_cooldown_suprime_cliques_repetidos():
    ctx, cfg = _ctx(criaturas=_det())
    m = _alvo(cfg)
    d1 = m.decidir(ctx, 0.0)
    assert d1.acao == TipoAcao.CLICAR
    m.confirmar_acao(d1, 0.0)

    d2 = m.decidir(ctx, 0.5)  # dentro do cooldown (2.0s)
    assert d2.acao == TipoAcao.NENHUMA
    assert "cooldown" in d2.motivo.lower()

    d3 = m.decidir(ctx, 2.5)  # fora do cooldown
    assert d3.acao == TipoAcao.CLICAR


def test_auto_cura_preempta_alvo_no_mesmo_tick():
    # HP crítico + criatura presente: curar (prioridade 100) vence atacar (80)
    ctx, cfg = _ctx(criaturas=_det(), hp=20)
    m = _motor(cfg, [AutoCura(cfg.cura, cfg.visao.confianca_minima), Alvo(cfg.alvo, cfg.visao.confianca_minima)])
    dec = m.decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.PRESSIONAR_TECLA
    assert dec.tecla == cfg.cura.tecla_cura_forte
