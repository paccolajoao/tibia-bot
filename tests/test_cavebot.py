"""Testes do comportamento Cavebot — OFFLINE, sintético.

A máquina de estados depende de dois sinais que o LOOP normalmente fornece:
`cavebot_acao_ts` (carimbado após executar a ação) e `minimap_movendo`. Aqui os
simulamos à mão em `estado_comportamentos`, como o loop faria.
"""

from __future__ import annotations

from bot.configuracao import Config, Waypoint
from bot.contexto import Contexto
from bot.decisao.comportamentos.auto_cura import AutoCura
from bot.decisao.comportamentos.cavebot import Cavebot
from bot.decisao.cooldown import GerenciadorCooldown
from bot.decisao.motor import MotorDecisao
from bot.decisao.tipos import TipoAcao
from bot.visao.tipos import DeteccaoCriaturas, LeituraBarra


def _cfg(waypoints, **kwargs):
    cfg = Config()
    cfg.cavebot.ativo = True
    cfg.cavebot.waypoints = waypoints
    cfg.cavebot.parado_ticks = kwargs.get("parado_ticks", 2)
    cfg.cavebot.timeout_trecho_s = kwargs.get("timeout_trecho_s", 8.0)
    cfg.cavebot.combate_timeout_s = kwargs.get("combate_timeout_s", 15.0)
    cfg.cavebot.limiar_troca_andar = kwargs.get("limiar_troca_andar", 25.0)
    cfg.cavebot.tentativas_troca = kwargs.get("tentativas_troca", 3)
    return cfg


def _ctx(cfg, ts=0.0):
    ctx = Contexto(config=cfg)
    ctx.ts = ts
    return ctx


def _executou(ctx, ts):
    """Simula o loop carimbando que a ação do cavebot saiu."""
    ctx.estado_comportamentos["cavebot_acao_ts"] = ts


def _combate(ctx, n=1):
    ctx.criaturas = DeteccaoCriaturas(n, False, 1.0, None, None)


def test_cede_ao_combate():
    cfg = _cfg([Waypoint(tipo="ir", x=10, y=20)])
    ctx = _ctx(cfg)
    ctx.criaturas = DeteccaoCriaturas(2, False, 1.0, None, None)
    assert Cavebot(cfg.cavebot).avaliar(ctx) is None


def test_emite_clique_no_minimapa():
    cfg = _cfg([Waypoint(tipo="ir", x=10, y=20)])
    ctx = _ctx(cfg)
    dec = Cavebot(cfg.cavebot).avaliar(ctx)
    assert dec.acao == TipoAcao.CLICAR
    assert dec.ponto == (10, 20)
    assert dec.dados["transformar"] is True
    assert dec.dados["recurso"] == "cavebot"
    assert dec.chave_cd == "cavebot"


def test_usar_emite_clique_direito():
    cfg = _cfg([Waypoint(tipo="usar", x=5, y=6)])
    dec = Cavebot(cfg.cavebot).avaliar(_ctx(cfg))
    assert dec.acao == TipoAcao.CLICAR_DIREITO
    assert dec.ponto == (5, 6)


def test_tecla_emite_pressionar():
    cfg = _cfg([Waypoint(tipo="tecla", tecla="f9")])
    dec = Cavebot(cfg.cavebot).avaliar(_ctx(cfg))
    assert dec.acao == TipoAcao.PRESSIONAR_TECLA
    assert dec.tecla == "f9"


def test_chega_quando_minimapa_para_e_avanca():
    cfg = _cfg(
        [Waypoint(tipo="ir", x=10, y=20), Waypoint(tipo="ir", x=30, y=40)],
        parado_ticks=2,
    )
    cb = Cavebot(cfg.cavebot)
    ctx = _ctx(cfg, ts=10.0)

    dec = cb.avaliar(ctx)  # emite clique p/ wp 0
    assert dec.ponto == (10, 20)
    _executou(ctx, 10.0)  # loop confirma execução

    # rolou (andando) por 1 tick
    ctx.ts = 10.1
    ctx.estado_comportamentos["minimap_movendo"] = True
    assert cb.avaliar(ctx) is None

    # parou por parado_ticks (2) -> chegou -> avança p/ wp 1
    ctx.ts = 10.2
    ctx.estado_comportamentos["minimap_movendo"] = False
    assert cb.avaliar(ctx) is None
    ctx.ts = 10.3
    assert cb.avaliar(ctx) is None  # 2º tick parado -> avança internamente

    # próximo tick emite o clique do wp 1
    ctx.ts = 10.4
    dec2 = cb.avaliar(ctx)
    assert dec2.acao == TipoAcao.CLICAR
    assert dec2.ponto == (30, 40)


def test_avanca_por_timeout():
    cfg = _cfg([Waypoint(tipo="ir", x=1, y=1), Waypoint(tipo="ir", x=2, y=2)], timeout_trecho_s=5.0)
    cb = Cavebot(cfg.cavebot)
    ctx = _ctx(cfg, ts=10.0)
    cb.avaliar(ctx)
    _executou(ctx, 10.0)
    # detecta a execução no tick seguinte (começa a contar a espera deste trecho)
    ctx.ts = 10.1
    ctx.estado_comportamentos["minimap_movendo"] = False
    assert cb.avaliar(ctx) is None
    # minimapa nunca rolou; passa o timeout -> avança mesmo assim
    ctx.ts = 16.0
    assert cb.avaliar(ctx) is None
    ctx.ts = 16.1
    dec = cb.avaliar(ctx)
    assert dec.ponto == (2, 2)


def test_rota_circular():
    cfg = _cfg([Waypoint(tipo="ir", x=1, y=1), Waypoint(tipo="ir", x=2, y=2)], parado_ticks=1)
    cb = Cavebot(cfg.cavebot)
    ctx = _ctx(cfg, ts=10.0)

    def chegar(t):
        _executou(ctx, t)
        ctx.ts = t + 0.1
        ctx.estado_comportamentos["minimap_movendo"] = True
        cb.avaliar(ctx)
        ctx.ts = t + 0.2
        ctx.estado_comportamentos["minimap_movendo"] = False
        cb.avaliar(ctx)

    d0 = cb.avaliar(ctx)
    assert d0.ponto == (1, 1)
    chegar(10.0)
    d1 = cb.avaliar(ctx)
    assert d1.ponto == (2, 2)
    chegar(11.0)
    d2 = cb.avaliar(ctx)  # voltou ao começo (circular)
    assert d2.ponto == (1, 1)


def test_esperar_nao_emite_e_avanca():
    cfg = _cfg([Waypoint(tipo="esperar", dwell_s=1.0), Waypoint(tipo="ir", x=9, y=9)])
    cb = Cavebot(cfg.cavebot)
    ctx = _ctx(cfg, ts=10.0)
    assert cb.avaliar(ctx) is None  # esperar não emite ação
    ctx.ts = 11.5  # passou o dwell -> avança
    assert cb.avaliar(ctx) is None
    ctx.ts = 11.6
    dec = cb.avaliar(ctx)
    assert dec.ponto == (9, 9)


def test_cavebot_perde_para_cura():
    cfg = _cfg([Waypoint(tipo="ir", x=1, y=1)])
    ctx = _ctx(cfg)
    ctx.hp = LeituraBarra(20.0, 1.0)  # HP crítico
    cooldown = GerenciadorCooldown({**cfg.cura.cooldown_s})
    motor = MotorDecisao(
        [AutoCura(cfg.cura, cfg.visao.confianca_minima), Cavebot(cfg.cavebot)], cooldown
    )
    dec = motor.decidir(ctx, 0.0)
    assert dec.acao == TipoAcao.PRESSIONAR_TECLA
    assert dec.tecla == cfg.cura.tecla_cura_forte


# ----------------------------- watchdog de combate (anti-stuck) -----------------------------

def test_combate_travado_volta_a_andar():
    # bicho inalcançável: criaturas presentes, mas nenhuma morte por combate_timeout_s.
    cfg = _cfg([Waypoint(tipo="ir", x=10, y=20)], combate_timeout_s=5.0)
    cb = Cavebot(cfg.cavebot)
    ctx = _ctx(cfg, ts=10.0)
    _combate(ctx, n=1)
    assert cb.avaliar(ctx) is None  # início do combate: cede
    ctx.ts = 16.0  # passou o combate_timeout_s sem matar nada
    dec = cb.avaliar(ctx)
    assert dec is not None and dec.acao == TipoAcao.CLICAR  # volta a navegar


def test_morte_recente_mantem_cedendo():
    cfg = _cfg([Waypoint(tipo="ir", x=10, y=20)], combate_timeout_s=5.0)
    cb = Cavebot(cfg.cavebot)
    ctx = _ctx(cfg, ts=10.0)
    _combate(ctx, n=2)
    assert cb.avaliar(ctx) is None
    ctx.ts = 16.0
    ctx.estado_comportamentos["saque_morte_ts"] = 15.9  # matou algo agora -> progresso
    assert cb.avaliar(ctx) is None  # reinicia o relógio: continua cedendo


def test_combate_timeout_zero_nunca_desiste():
    cfg = _cfg([Waypoint(tipo="ir", x=10, y=20)], combate_timeout_s=0.0)
    cb = Cavebot(cfg.cavebot)
    ctx = _ctx(cfg, ts=10.0)
    _combate(ctx, n=1)
    assert cb.avaliar(ctx) is None
    ctx.ts = 999.0
    assert cb.avaliar(ctx) is None  # 0 = nunca desiste


# ----------------------------- validação de troca de andar -----------------------------

def test_troca_andar_confirma_por_pico_do_minimapa():
    cfg = _cfg(
        [Waypoint(tipo="usar", x=1, y=1, troca_andar=True, dwell_s=0.0), Waypoint(tipo="ir", x=2, y=2)],
        limiar_troca_andar=25.0,
    )
    cb = Cavebot(cfg.cavebot)
    ctx = _ctx(cfg, ts=10.0)
    d0 = cb.avaliar(ctx)
    assert d0.acao == TipoAcao.CLICAR_DIREITO  # usar = clique-direito
    _executou(ctx, 10.0)
    ctx.ts = 10.1
    ctx.estado_comportamentos["minimap_score"] = 5.0  # sem pico ainda
    assert cb.avaliar(ctx) is None
    ctx.ts = 10.2
    ctx.estado_comportamentos["minimap_score"] = 40.0  # pico -> troca confirmada
    assert cb.avaliar(ctx) is None  # dwell_s=0 -> avança no mesmo tick
    ctx.ts = 10.3
    d1 = cb.avaliar(ctx)
    assert d1.acao == TipoAcao.CLICAR and d1.ponto == (2, 2)  # próximo waypoint


def test_troca_andar_retenta_e_segue_apos_esgotar():
    cfg = _cfg(
        [Waypoint(tipo="usar", x=1, y=1, troca_andar=True, dwell_s=0.0), Waypoint(tipo="ir", x=2, y=2)],
        limiar_troca_andar=25.0,
        timeout_trecho_s=1.0,
        tentativas_troca=2,
    )
    cb = Cavebot(cfg.cavebot)
    ctx = _ctx(cfg, ts=10.0)
    cb.avaliar(ctx)  # emite a 1ª tentativa
    _executou(ctx, 10.0)
    ctx.ts = 10.1
    ctx.estado_comportamentos["minimap_score"] = 0.0  # nunca tem pico
    assert cb.avaliar(ctx) is None
    ctx.ts = 11.2  # estoura o timeout -> re-tenta (não avança)
    assert cb.avaliar(ctx) is None
    ctx.ts = 11.3
    d_retry = cb.avaliar(ctx)  # re-emite a ação (ainda no waypoint 0)
    assert d_retry.acao == TipoAcao.CLICAR_DIREITO and d_retry.ponto == (1, 1)
    _executou(ctx, 11.3)
    ctx.ts = 11.4
    assert cb.avaliar(ctx) is None
    ctx.ts = 12.5  # 2º timeout -> esgota tentativas -> avança best-effort
    assert cb.avaliar(ctx) is None
    ctx.ts = 12.6
    d_next = cb.avaliar(ctx)
    assert d_next.ponto == (2, 2)  # seguiu p/ o próximo waypoint (não travou)
