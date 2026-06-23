"""Testes do comportamento MagiaAtaque — OFFLINE, sintético."""

from __future__ import annotations

from bot.configuracao import Config, MagiaAtaqueConfig
from bot.contexto import Contexto
from bot.decisao.comportamentos.auto_cura import AutoCura
from bot.decisao.comportamentos.magia_ataque import MagiaAtaque
from bot.decisao.cooldown import GerenciadorCooldown
from bot.decisao.motor import MotorDecisao
from bot.decisao.tipos import TipoAcao
from bot.visao.tipos import DeteccaoCriaturas, LeituraBarra


def _cfg(**kw) -> MagiaAtaqueConfig:
    return MagiaAtaqueConfig(ativo=True, tecla="f7", **kw)


def _ctx(n_criaturas=1, mana=None) -> Contexto:
    ctx = Contexto(config=Config())
    ctx.ts = 10.0
    ctx.criaturas = DeteccaoCriaturas(n_criaturas, False, 1.0, None, None)
    if mana is not None:
        ctx.mana = LeituraBarra(mana, 1.0)
    return ctx


def test_ataca_em_combate():
    dec = MagiaAtaque(_cfg()).avaliar(_ctx(n_criaturas=2))
    assert dec is not None
    assert dec.acao == TipoAcao.PRESSIONAR_TECLA
    assert dec.tecla == "f7"
    assert dec.chave_cd == "magia_ataque"
    assert dec.dados["recurso"] == "magia_ataque"


def test_nao_ataca_sem_criaturas():
    assert MagiaAtaque(_cfg()).avaliar(_ctx(n_criaturas=0)) is None


def test_inativo_nao_age():
    cfg = MagiaAtaqueConfig(ativo=False, tecla="f7")
    assert MagiaAtaque(cfg).avaliar(_ctx()) is None


def test_respeita_piso_de_mana():
    cfg = _cfg(mana_minima=30.0)
    # mana acima do piso -> ataca
    assert MagiaAtaque(cfg).avaliar(_ctx(mana=50.0)) is not None
    # mana abaixo do piso -> não ataca (preserva p/ cura)
    assert MagiaAtaque(cfg).avaliar(_ctx(mana=20.0)) is None


def test_mana_confianca_baixa_nao_bloqueia():
    cfg = _cfg(mana_minima=30.0, confianca_minima=0.6)
    ctx = _ctx()
    ctx.mana = LeituraBarra(10.0, 0.2)  # mana baixa MAS leitura não-confiável -> ignora o piso
    assert MagiaAtaque(cfg).avaliar(ctx) is not None


def test_cooldown_espaca_os_casts():
    cfg = _cfg(intervalo_s=2.0)
    cooldown = GerenciadorCooldown({"magia_ataque": cfg.intervalo_s})
    motor = MotorDecisao([MagiaAtaque(cfg)], cooldown)
    ctx = _ctx()
    d1 = motor.decidir(ctx, 0.0)
    assert d1.acao == TipoAcao.PRESSIONAR_TECLA
    motor.confirmar_acao(d1, 0.0)
    d2 = motor.decidir(ctx, 0.5)  # dentro do intervalo
    assert d2.acao == TipoAcao.NENHUMA
    d3 = motor.decidir(ctx, 2.5)  # passou
    assert d3.acao == TipoAcao.PRESSIONAR_TECLA


def test_cura_preempta_magia_ataque():
    cfg = _cfg()
    ctx = _ctx()
    ctx.hp = LeituraBarra(20.0, 1.0)  # HP crítico
    base = Config()
    cooldown = GerenciadorCooldown({**base.cura.cooldown_s, "magia_ataque": cfg.intervalo_s})
    motor = MotorDecisao(
        [AutoCura(base.cura, base.visao.confianca_minima), MagiaAtaque(cfg)], cooldown
    )
    dec = motor.decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.PRESSIONAR_TECLA
    assert dec.tecla == base.cura.tecla_cura_forte
