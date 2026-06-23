"""Teste de integração do LoopBot — headless, com captura e entrada FALSAS.

Prova o pipeline inteiro (captura -> visão -> decisão -> input -> telemetria) sem
o jogo: HP baixo numa imagem sintética deve disparar a cura forte.
"""

from __future__ import annotations

import numpy as np

from bot.captura.base import Frame
from bot.configuracao import Config
from bot.contexto import Contexto
from bot.decisao.comportamentos.alvo import Alvo
from bot.decisao.comportamentos.auto_cura import AutoCura
from bot.decisao.comportamentos.comer import Comer
from bot.decisao.comportamentos.saque import Saque
from bot.decisao.cooldown import GerenciadorCooldown
from bot.decisao.motor import MotorDecisao
from bot.entrada.simulada import EntradaSimulada
from bot.nucleo.estado_execucao import ControladorExecucao
from bot.nucleo.loop_bot import LoopBot
from bot.telemetria.barramento import BarramentoEventos


class CapFake:
    nome_backend = "fake"

    def __init__(self, imagem):
        self._img = imagem

    def iniciar(self):
        pass

    def capturar(self, regiao=None):
        return Frame(self._img, 0.0, None)  # regiao=None => regiões usadas como coords da imagem

    def parar(self):
        pass


class CapKill:
    """Captura que devolve a imagem de barras para a região combinada e, para a região
    da battle list, uma criatura nos primeiros N grabs e depois vazio (simula uma morte).
    """

    nome_backend = "fake"

    def __init__(self, img_barras, reg_battle, img_criatura, img_vazio, grabs_com_criatura=2):
        self._barras = img_barras
        self._reg_battle = reg_battle
        self._criatura = img_criatura
        self._vazio = img_vazio
        self._grabs_com_criatura = grabs_com_criatura
        self._n_battle = 0

    def iniciar(self):
        pass

    def capturar(self, regiao=None):
        if regiao == self._reg_battle:
            self._n_battle += 1
            img = self._criatura if self._n_battle <= self._grabs_com_criatura else self._vazio
            return Frame(img, 0.0, regiao)
        return Frame(self._barras, 0.0, regiao)

    def parar(self):
        pass


class CapErro:
    """Captura que SEMPRE levanta — prova que a rede de segurança do tick não derruba
    a thread (o loop loga o erro e segue até max_ticks)."""

    nome_backend = "fake"

    def __init__(self):
        self.chamadas = 0

    def iniciar(self):
        pass

    def capturar(self, regiao=None):
        self.chamadas += 1
        raise RuntimeError("falha sintética de captura")

    def parar(self):
        pass


class SegFake:
    def janela_focada(self):
        return True


def _imagem(fazer_barra):
    img = np.empty((60, 200, 3), np.uint8)
    img[:] = (15, 15, 15)
    img[2:16, 5:125] = fazer_barra(20)                                # HP 20% (vermelho)
    img[22:36, 5:125] = fazer_barra(80, cor_preench=(200, 0, 0))      # Mana 80% (azul)
    return img


def test_loop_dispara_cura_quando_hp_baixo(fazer_barra):
    cfg = Config()
    cfg.regioes.hp = (5, 2, 125, 16)
    cfg.regioes.mana = (5, 22, 125, 36)
    cfg.captura.fps_alvo = 1000  # roda rápido no teste

    ctx = Contexto(config=cfg)
    bus = BarramentoEventos(maxsize=10000)
    ctrl = ControladorExecucao()
    motor = MotorDecisao(
        [AutoCura(cfg.cura, cfg.visao.confianca_minima)],
        GerenciadorCooldown(cfg.cura.cooldown_s),
    )
    entrada = EntradaSimulada()

    loop = LoopBot(ctx, CapFake(_imagem(fazer_barra)), entrada, motor, ctrl, SegFake(), bus, max_ticks=3)
    loop.run()  # síncrono até max_ticks

    # HP 20% <= crítico (35%) -> cura forte; cooldown impede repetir nos ticks seguintes
    assert cfg.cura.tecla_cura_forte in entrada.teclas
    assert entrada.teclas.count(cfg.cura.tecla_cura_forte) == 1
    assert ctx.estatisticas.curas == 1


def _imagem_com_criatura(fazer_barra):
    img = np.empty((100, 200, 3), np.uint8)
    img[:] = (15, 15, 15)
    img[2:16, 5:125] = fazer_barra(100)                          # HP cheio (não cura)
    img[22:36, 5:125] = fazer_barra(100, cor_preench=(200, 0, 0))  # Mana cheia
    img[50:56, 5:130] = (0, 200, 0)                              # mini HP-bar de criatura (verde)
    return img


def test_loop_clica_na_battle_list_quando_ha_criatura(fazer_barra):
    cfg = Config()
    cfg.regioes.hp = (5, 2, 125, 16)
    cfg.regioes.mana = (5, 22, 125, 36)
    cfg.regioes.battle_list = (0, 45, 200, 100)
    cfg.captura.fps_alvo = 1000

    ctx = Contexto(config=cfg)
    bus = BarramentoEventos(maxsize=10000)
    ctrl = ControladorExecucao()
    motor = MotorDecisao(
        [AutoCura(cfg.cura, cfg.visao.confianca_minima), Alvo(cfg.alvo, cfg.visao.confianca_minima)],
        GerenciadorCooldown({**cfg.cura.cooldown_s, **cfg.alvo.cooldown_s}),
    )
    entrada = EntradaSimulada()

    loop = LoopBot(
        ctx, CapFake(_imagem_com_criatura(fazer_barra)), entrada, motor, ctrl, SegFake(), bus, max_ticks=3
    )
    loop.run()

    # criatura presente, sem alvo, HP cheio -> clica 1x (cooldown impede repetir)
    assert len(entrada.cliques) == 1
    assert ctx.estatisticas.ataques == 1
    assert entrada.teclas == []  # nada de cura


def _imagem_barras_cheias(fazer_barra):
    img = np.empty((100, 200, 3), np.uint8)
    img[:] = (15, 15, 15)
    img[2:16, 5:125] = fazer_barra(100)                           # HP cheio
    img[22:36, 5:125] = fazer_barra(100, cor_preench=(200, 0, 0))  # Mana cheia
    return img


def _battle_img(com_criatura):
    img = np.empty((55, 200, 3), np.uint8)
    img[:] = (15, 15, 15)
    if com_criatura:
        img[25:31, 5:130] = (0, 200, 0)  # mini HP-bar de criatura (verde)
    return img


def test_loop_quick_loot_quando_criatura_morre(fazer_barra):
    cfg = Config()
    cfg.regioes.hp = (5, 2, 125, 16)
    cfg.regioes.mana = (5, 22, 125, 36)
    cfg.regioes.battle_list = (0, 45, 200, 100)
    cfg.captura.fps_alvo = 1000
    cfg.comer.ativo = False  # isola o saque

    ctx = Contexto(config=cfg)
    bus = BarramentoEventos(maxsize=10000)
    ctrl = ControladorExecucao()
    motor = MotorDecisao(
        [
            AutoCura(cfg.cura, cfg.visao.confianca_minima),
            Alvo(cfg.alvo, cfg.visao.confianca_minima),
            Saque(cfg.saque),
        ],
        GerenciadorCooldown({**cfg.cura.cooldown_s, **cfg.alvo.cooldown_s}),
    )
    entrada = EntradaSimulada()

    cap = CapKill(
        _imagem_barras_cheias(fazer_barra),
        (0, 45, 200, 100),
        _battle_img(com_criatura=True),
        _battle_img(com_criatura=False),
        grabs_com_criatura=2,
    )
    loop = LoopBot(ctx, cap, entrada, motor, ctrl, SegFake(), bus, max_ticks=4)
    loop.run()

    # criatura presente -> ataca; depois some (morre) -> Quick Loot
    assert cfg.saque.tecla in entrada.teclas
    assert ctx.estatisticas.saques >= 1
    assert ctx.estatisticas.ataques >= 1


def test_loop_auto_comer_por_tempo(fazer_barra):
    cfg = Config()
    cfg.regioes.hp = (5, 2, 125, 16)
    cfg.regioes.mana = (5, 22, 125, 36)
    cfg.captura.fps_alvo = 1000

    ctx = Contexto(config=cfg)
    bus = BarramentoEventos(maxsize=10000)
    ctrl = ControladorExecucao()
    motor = MotorDecisao([Comer(cfg.comer)], GerenciadorCooldown({}))
    entrada = EntradaSimulada()

    loop = LoopBot(ctx, CapFake(_imagem_barras_cheias(fazer_barra)), entrada, motor, ctrl, SegFake(), bus, max_ticks=3)
    loop.run()

    # come no 1º tick (intervalo grande impede repetir nos ticks seguintes do teste)
    assert entrada.teclas.count(cfg.comer.tecla) == 1
    assert ctx.estatisticas.refeicoes == 1


def test_loop_sobrevive_a_excecao_no_tick():
    # Rede de segurança: uma exceção a cada tick NÃO derruba a thread nem trava o loop;
    # ele loga e segue, respeitando max_ticks (sem isso, run() levantaria e o bot congelaria).
    cfg = Config()
    cfg.regioes.hp = (5, 2, 125, 16)
    cfg.regioes.mana = (5, 22, 125, 36)
    cfg.captura.fps_alvo = 1000

    ctx = Contexto(config=cfg)
    bus = BarramentoEventos(maxsize=10000)
    ctrl = ControladorExecucao()
    motor = MotorDecisao(
        [AutoCura(cfg.cura, cfg.visao.confianca_minima)], GerenciadorCooldown(cfg.cura.cooldown_s)
    )
    cap = CapErro()
    loop = LoopBot(ctx, cap, EntradaSimulada(), motor, ctrl, SegFake(), bus, max_ticks=3)

    loop.run()  # não deve levantar nem travar

    assert ctx.tick == 3       # rodou os 3 ticks apesar do erro em cada um
    assert cap.chamadas >= 3   # tentou capturar todo tick
