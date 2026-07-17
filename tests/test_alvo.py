"""Testes do comportamento Alvo e sua integração no motor — OFFLINE, sintético."""

from __future__ import annotations

from bot.configuracao import Config
from bot.contexto import Contexto
from bot.decisao.comportamentos.alvo import Alvo
from bot.decisao.comportamentos.camada_cura import cooldowns_cura, montar_camadas_cura
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
    cooldown = GerenciadorCooldown({**cooldowns_cura(cfg.cura), **cfg.alvo.cooldown_s})
    return MotorDecisao(comportamentos, cooldown)


def _alvo(cfg):
    return _motor(cfg, [Alvo(cfg.alvo, cfg.visao.confianca_minima)])


def test_clica_quando_criatura_sem_alvo():
    ctx, cfg = _ctx(criaturas=_det(n=2, alvo_atual=False))
    dec = _alvo(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.CLICAR
    assert dec.ponto == (110, 205)
    assert dec.chave_cd == "atacar"


def test_alvo_atual_nao_bloqueia_ataque():
    # `alvo_atual` (realce vermelho) é leitura não-confiável (confunde com HP avermelhado):
    # NÃO deve impedir o ataque. Sem engajamento prévio, ataca mesmo com alvo_atual=True.
    ctx, cfg = _ctx(criaturas=_det(n=2, alvo_atual=True))
    dec = _alvo(cfg).decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.CLICAR


def test_reataca_proximo_apos_morte_mesmo_com_alvo_atual():
    # Regressão: mata 1 de vários e os restantes (feridos -> barra avermelhada) fariam
    # alvo_atual=True. A morte (queda na contagem) deve destravar o re-ataque mesmo assim.
    ctx, cfg = _ctx(criaturas=_det(n=2, alvo_atual=True))
    ctx.estado_comportamentos["alvo_engajado_ts"] = 0.0
    ctx.estado_comportamentos["saque_morte_ts"] = 0.5
    ctx.ts = 0.6
    dec = _alvo(cfg).decidir(ctx, 0.6)
    assert dec.acao == TipoAcao.CLICAR


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


def test_nao_retroca_alvo_enquanto_engajado():
    # já atacamos um alvo (engajado em t=0); dentro de recompromisso_s e sem kill -> não re-ataca
    ctx, cfg = _ctx(criaturas=_det(n=2, alvo_atual=False))
    ctx.estado_comportamentos["alvo_engajado_ts"] = 0.0
    ctx.ts = 1.0
    dec = _alvo(cfg).decidir(ctx, 1.0)
    assert dec.acao == TipoAcao.NENHUMA


def test_reataca_apos_criatura_morrer():
    # engajado em t=0; uma criatura morreu em t=0.5 -> precisa de novo alvo -> ataca
    ctx, cfg = _ctx(criaturas=_det(n=2, alvo_atual=False))
    ctx.estado_comportamentos["alvo_engajado_ts"] = 0.0
    ctx.estado_comportamentos["saque_morte_ts"] = 0.5
    ctx.ts = 1.0
    dec = _alvo(cfg).decidir(ctx, 1.0)
    assert dec.acao == TipoAcao.CLICAR


def test_reataca_apos_timeout_de_recompromisso():
    # engajado em t=0, sem kill; passou de recompromisso_s (3s) -> rede de segurança ataca
    ctx, cfg = _ctx(criaturas=_det(n=1, alvo_atual=False))
    ctx.estado_comportamentos["alvo_engajado_ts"] = 0.0
    ctx.ts = 5.0
    dec = _alvo(cfg).decidir(ctx, 5.0)
    assert dec.acao == TipoAcao.CLICAR


# ----------------------------- watchdog "sem dano" (anti-travamento, log-only) -----------------------------
# Convenção (igual a test_cavebot.py): nunca usar ts=0.0 como a 1ª chamada do watchdog —
# `_engajado_desde == 0.0` é o sentinela de "ainda não semeado" (mirror do `_combate_inicio`
# do Cavebot), então uma 1ª chamada em ts=0.0 faria a semeadura colidir com o sentinela.


def test_avisa_sem_dano_apos_timeout():
    # engajado em t=10; a 1ª chamada (fora do recompromisso_s) semeia o relógio do
    # watchdog; a 2ª, 11s depois e sem sinal de dano/morte, já passou do timeout (10s).
    ctx, cfg = _ctx(criaturas=_det(n=1, alvo_atual=False))
    ctx.estado_comportamentos["alvo_engajado_ts"] = 10.0
    m = _alvo(cfg)
    ctx.ts = 12.0
    dec1 = m.decidir(ctx, 12.0)
    assert dec1.acao == TipoAcao.CLICAR
    assert "sem dano" not in dec1.motivo
    ctx.ts = 23.0
    dec2 = m.decidir(ctx, 23.0)
    assert dec2.acao == TipoAcao.CLICAR
    assert "sem dano" in dec2.motivo


def test_nao_avisa_dentro_do_timeout():
    ctx, cfg = _ctx(criaturas=_det(n=1, alvo_atual=False))
    ctx.estado_comportamentos["alvo_engajado_ts"] = 10.0
    m = _alvo(cfg)
    ctx.ts = 12.0
    dec1 = m.decidir(ctx, 12.0)
    assert "sem dano" not in dec1.motivo
    ctx.ts = 20.0  # só 8s desde a semeadura (12.0) -> ainda dentro do timeout (10s)
    dec2 = m.decidir(ctx, 20.0)
    assert dec2.acao == TipoAcao.CLICAR
    assert "sem dano" not in dec2.motivo


def test_dano_reseta_relogio_sem_dano():
    ctx, cfg = _ctx(criaturas=_det(n=1, alvo_atual=False))
    ctx.estado_comportamentos["alvo_engajado_ts"] = 10.0
    m = _alvo(cfg)
    ctx.ts = 12.0
    m.decidir(ctx, 12.0)  # semeia o relógio em t=12
    ctx.ts = 18.0
    ctx.estado_comportamentos["alvo_dano_ts"] = 17.9  # dano observado -> reseta o relógio
    dec2 = m.decidir(ctx, 18.0)
    assert "sem dano" not in dec2.motivo  # só 0.1s desde o reset
    ctx.ts = 21.0  # 11s desde a semeadura ORIGINAL (12.0), mas só 3s desde o dano (18.0)
    dec3 = m.decidir(ctx, 21.0)
    assert "sem dano" not in dec3.motivo


def test_morte_reseta_relogio_sem_dano():
    ctx, cfg = _ctx(criaturas=_det(n=1, alvo_atual=False))
    ctx.estado_comportamentos["alvo_engajado_ts"] = 10.0
    m = _alvo(cfg)
    ctx.ts = 12.0
    m.decidir(ctx, 12.0)  # semeia o relógio em t=12
    ctx.ts = 18.0
    ctx.estado_comportamentos["saque_morte_ts"] = 17.9  # matou algo -> reseta o relógio
    dec2 = m.decidir(ctx, 18.0)
    assert "sem dano" not in dec2.motivo
    ctx.ts = 21.0
    dec3 = m.decidir(ctx, 21.0)
    assert "sem dano" not in dec3.motivo


def test_sem_dano_timeout_zero_desliga_aviso():
    ctx, cfg = _ctx(criaturas=_det(n=1, alvo_atual=False))
    cfg.alvo.sem_dano_timeout_s = 0.0
    ctx.estado_comportamentos["alvo_engajado_ts"] = 10.0
    m = _alvo(cfg)
    ctx.ts = 12.0
    m.decidir(ctx, 12.0)
    ctx.ts = 100.0
    dec = m.decidir(ctx, 100.0)
    assert "sem dano" not in dec.motivo


def test_auto_cura_preempta_alvo_no_mesmo_tick():
    # HP crítico + criatura presente: curar (prioridade 106) vence atacar (80)
    ctx, cfg = _ctx(criaturas=_det(), hp=20)
    m = _motor(
        cfg,
        [*montar_camadas_cura(cfg.cura, cfg.visao.confianca_minima), Alvo(cfg.alvo, cfg.visao.confianca_minima)],
    )
    dec = m.decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.PRESSIONAR_TECLA
    assert dec.tecla == cfg.cura.tecla_cura_forte
