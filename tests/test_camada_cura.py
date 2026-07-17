"""Testes das camadas de cura — cascata, cooldown compartilhado de poções e trava de HP.

OFFLINE, com contextos sintéticos. Avança os cooldowns chamando `confirmar_acao`
entre os `decidir`, como o loop faria após executar cada ação.
"""

from __future__ import annotations

from bot.configuracao import Config
from bot.contexto import Contexto
from bot.decisao.comportamentos.camada_cura import cooldowns_cura, montar_camadas_cura
from bot.decisao.cooldown import GerenciadorCooldown
from bot.decisao.motor import MotorDecisao
from bot.decisao.tipos import Decisao, TipoAcao
from bot.telemetria.estatisticas import Estatisticas
from bot.visao.tipos import LeituraBarra


def _motor(cfg):
    return MotorDecisao(
        montar_camadas_cura(cfg.cura, cfg.visao.confianca_minima),
        GerenciadorCooldown(cooldowns_cura(cfg.cura)),
    )


def _ctx(cfg, hp=None, mana=None, confianca=1.0):
    ctx = Contexto(config=cfg)
    if hp is not None:
        ctx.hp = LeituraBarra(hp, confianca)
    if mana is not None:
        ctx.mana = LeituraBarra(mana, confianca)
    return ctx


def test_pocao_e_cura_leve_empilham_em_ticks_adjacentes():
    # HP amarelo: poção de vida (tick 1) e exura ico (tick 2) saem em ticks adjacentes,
    # pois estão em grupos de cooldown diferentes (mesmo "turno" do Tibia).
    cfg = Config()  # hp_pocao_vida=65, hp_baixo=90
    ctx = _ctx(cfg, hp=55)  # dispara poção de vida E cura leve; não dispara cura forte
    m = _motor(cfg)

    d1 = m.decidir(ctx, 0.0)
    assert d1.tecla == cfg.cura.tecla_pocao_vida
    m.confirmar_acao(d1, 0.0)

    d2 = m.decidir(ctx, 0.066)
    assert d2.tecla == cfg.cura.tecla_cura_leve


def test_grupo_pocao_bloqueia_segunda_pocao():
    # Poção de vida e de mana compartilham a chave "grupo_pocao": só uma por cd_pocao.
    cfg = Config()
    cfg.cura.mana_hp_seguro = 0.0  # desliga a trava de HP p/ isolar o cooldown
    cfg.cura.hp_critico = 10.0
    cfg.cura.hp_baixo = 30.0  # HP 55 não dispara magia; só a poção de vida
    ctx = _ctx(cfg, hp=55, mana=20)
    m = _motor(cfg)

    d1 = m.decidir(ctx, 0.0)
    assert d1.tecla == cfg.cura.tecla_pocao_vida
    m.confirmar_acao(d1, 0.0)

    # mesma janela: a poção de mana quer disparar mas compartilha o cooldown -> NENHUMA
    d2 = m.decidir(ctx, 0.066)
    assert d2.acao == TipoAcao.NENHUMA
    assert "cooldown" in d2.motivo.lower()

    # HP recuperado + cooldown de poção expirado -> agora bebe mana
    ctx2 = _ctx(cfg, hp=95, mana=20)
    d3 = m.decidir(ctx2, 1.2)
    assert d3.tecla == cfg.cura.tecla_pocao_mana


def test_cura_forte_bloqueada_cede_para_camada_menor():
    # A magia de emergência tem cd longo; bloqueada, NÃO impede a poção de vida de sair.
    cfg = Config()
    ctx = _ctx(cfg, hp=20)  # dispara todas as camadas de HP
    m = _motor(cfg)

    d1 = m.decidir(ctx, 0.0)
    assert d1.tecla == cfg.cura.tecla_cura_forte
    m.confirmar_acao(d1, 0.0)

    d2 = m.decidir(ctx, 0.066)
    assert d2.tecla == cfg.cura.tecla_pocao_vida  # cede para a de menor prioridade


def test_pocao_mana_respeita_trava_hp():
    # Com HP baixo (dentro da faixa de risco), não bebe poção de mana — reserva o
    # cooldown compartilhado das poções para a vida.
    cfg = Config()
    cfg.cura.hp_critico = 30.0
    cfg.cura.hp_pocao_vida = 45.0
    cfg.cura.hp_baixo = 40.0  # HP 50 não dispara nenhuma camada de HP
    cfg.cura.mana_hp_seguro = 70.0
    m = _motor(cfg)

    ctx_hp_baixo = _ctx(cfg, hp=50, mana=20)
    dec = m.decidir(ctx_hp_baixo, 0.0)
    assert dec.acao == TipoAcao.NENHUMA  # trava de HP bloqueia a poção de mana

    ctx_hp_ok = _ctx(cfg, hp=95, mana=20)
    dec2 = m.decidir(ctx_hp_ok, 0.0)
    assert dec2.tecla == cfg.cura.tecla_pocao_mana


def test_registrar_acao_pocao_vida_nao_infla_curas():
    # Guarda a regressão do elif-antes-do-else em estatisticas.registrar_acao.
    est = Estatisticas()
    est.registrar_acao(Decisao("pocao_vida", TipoAcao.PRESSIONAR_TECLA, "f2", "m", 104, {"recurso": "pocao_vida"}))
    assert est.pocoes_vida == 1
    assert est.curas == 0  # poção de vida NÃO conta como cura de magia

    est.registrar_acao(Decisao("pocao_mana", TipoAcao.PRESSIONAR_TECLA, "f1", "m", 100, {"recurso": "mana"}))
    assert est.pocoes_mana == 1

    est.registrar_acao(
        Decisao("cura_leve", TipoAcao.PRESSIONAR_TECLA, "f6", "m", 102, {"recurso": "hp", "nivel": "baixo"})
    )
    assert est.curas == 1
    assert est.curas_leve == 1
