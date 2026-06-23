"""Entrypoint principal: sobe o loop do bot (thread) + o painel web (uvicorn).

Uso:  python executar.py   (de preferência num terminal como Administrador)
"""

from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from bot.captura.fabrica import criar_capturador  # noqa: E402
from bot.contexto import Contexto  # noqa: E402
from bot.decisao.comportamentos.alvo import Alvo  # noqa: E402
from bot.decisao.comportamentos.auto_cura import AutoCura  # noqa: E402
from bot.decisao.comportamentos.cavebot import (
    CHAVE_COOLDOWN as CHAVE_COOLDOWN_CAVEBOT,  # noqa: E402
)
from bot.decisao.comportamentos.cavebot import Cavebot  # noqa: E402
from bot.decisao.comportamentos.comer import Comer  # noqa: E402
from bot.decisao.comportamentos.drop import Drop  # noqa: E402
from bot.decisao.comportamentos.magia_ataque import (
    CHAVE_COOLDOWN as CHAVE_COOLDOWN_MAGIA,  # noqa: E402
)
from bot.decisao.comportamentos.magia_ataque import MagiaAtaque  # noqa: E402
from bot.decisao.comportamentos.saque import Saque  # noqa: E402
from bot.decisao.comportamentos.usar_mana import (
    CHAVE_COOLDOWN as CHAVE_COOLDOWN_USAR_MANA,  # noqa: E402
)
from bot.decisao.comportamentos.usar_mana import UsarMana  # noqa: E402
from bot.decisao.cooldown import GerenciadorCooldown  # noqa: E402
from bot.decisao.motor import MotorDecisao  # noqa: E402
from bot.entrada.teclado_directinput import EntradaDirectInput  # noqa: E402
from bot.nucleo.estado_execucao import ControladorExecucao, EstadoExecucao  # noqa: E402
from bot.nucleo.loop_bot import LoopBot  # noqa: E402
from bot.nucleo.seguranca import Seguranca  # noqa: E402
from bot.painel.servidor import criar_app  # noqa: E402
from bot.persistencia import obter_ativo  # noqa: E402
from bot.telemetria.barramento import BarramentoEventos  # noqa: E402
from bot.telemetria.eventos import LinhaRaciocinio  # noqa: E402


def _montar_loop(cfg, controlador, barramento, log) -> LoopBot:
    """Monta o loop do bot a partir do Config ativo (capturador + comportamentos)."""
    capturador = criar_capturador(
        cfg.captura.backend,
        cfg.captura.monitor,
        log,
        tibia_screenshots=cfg.captura.tibia_screenshots,
        hotkey_screenshot=cfg.captura.hotkey_screenshot,
        fps_alvo=cfg.captura.fps_alvo,
        obs_device_index=cfg.captura.obs_device_index,
        obs_device_nome=cfg.captura.obs_device_nome,
        obs_largura=cfg.captura.obs_largura,
        obs_altura=cfg.captura.obs_altura,
    )
    entrada = EntradaDirectInput(cfg.entrada.atraso_pre_ms, cfg.entrada.atraso_pos_ms)
    # cooldown do usar-mana é chaveado pela CHAVE_COOLDOWN da Decisao ("usar_mana"),
    # não pela tecla — senão o motor consulta uma chave que não existe no gerenciador.
    usar_mana_cd = {CHAVE_COOLDOWN_USAR_MANA: cfg.usar_mana.cooldown_s} if cfg.usar_mana.ativo else {}
    cavebot_cd = {CHAVE_COOLDOWN_CAVEBOT: cfg.cavebot.cooldown_s} if cfg.cavebot.ativo else {}
    magia_cd = {CHAVE_COOLDOWN_MAGIA: cfg.magia_ataque.intervalo_s} if cfg.magia_ataque.ativo else {}
    cooldown = GerenciadorCooldown(
        {**cfg.cura.cooldown_s, **cfg.alvo.cooldown_s, **usar_mana_cd, **cavebot_cd, **magia_cd}
    )
    comportamentos = []
    if cfg.cura.ativo:
        comportamentos.append(AutoCura(cfg.cura, cfg.visao.confianca_minima))
    else:
        log("Auto-cura desligada (recurso desativado na config)", "alerta")
    if cfg.regioes.battle_list_calibrado:
        if cfg.alvo.ativo:
            comportamentos.append(Alvo(cfg.alvo, cfg.visao.confianca_minima))
            log("Targeting habilitado (battle list calibrada)")
            if cfg.saque.ativo:
                comportamentos.append(Saque(cfg.saque))
                log(f"Auto-loot (Quick Loot) habilitado -> tecla {cfg.saque.tecla.upper()}")
        else:
            log("Targeting desligado (recurso desativado na config)")
    else:
        log("Targeting/auto-loot desligados — battle list não calibrada (rode calibrar.py)")
    if cfg.magia_ataque.ativo:
        if cfg.regioes.battle_list_calibrado:
            comportamentos.append(MagiaAtaque(cfg.magia_ataque))
            log(
                f"Magia de ataque habilitada -> tecla {cfg.magia_ataque.tecla.upper()}"
                f" (piso de mana {cfg.magia_ataque.mana_minima:.0f}%)"
            )
        else:
            log("Magia de ataque ligada mas battle list não calibrada (não sabe quando há combate) — desativada", "alerta")
    if cfg.usar_mana.ativo:
        comportamentos.append(UsarMana(cfg.usar_mana))
        log(
            f"Usar-mana habilitado -> tecla {cfg.usar_mana.tecla.upper()}"
            f" (mana {cfg.usar_mana.mana_alto:.0f}% -> {cfg.usar_mana.mana_alvo:.0f}%)"
        )
    if cfg.comer.ativo:
        comportamentos.append(Comer(cfg.comer))
        log(f"Auto-comer habilitado -> tecla {cfg.comer.tecla.upper()} a cada {cfg.comer.intervalo_s:.0f}s")
    if cfg.drop.ativo:
        if cfg.regioes.drop_calibrado and cfg.drop.itens:
            comportamentos.append(Drop(cfg.drop))
            log(f"Drop de loot habilitado -> {len(cfg.drop.itens)} item(ns) cadastrado(s)")
        else:
            log("Drop de loot ligado mas sem itens ou sem inventário/tile calibrado — desativado", "alerta")
    if cfg.cavebot.ativo:
        if cfg.regioes.minimap_calibrado and cfg.cavebot.waypoints:
            comportamentos.append(Cavebot(cfg.cavebot))
            log(f"Cavebot habilitado -> {len(cfg.cavebot.waypoints)} waypoint(s)")
        else:
            log("Cavebot ligado mas sem waypoints ou sem minimapa calibrado — desativado", "alerta")
    motor = MotorDecisao(comportamentos, cooldown)
    seguranca = Seguranca(controlador, cfg.seguranca, log)
    seguranca.registrar_hotkeys()

    contexto = Contexto(config=cfg)
    return LoopBot(contexto, capturador, entrada, motor, controlador, seguranca, barramento)


def main() -> int:
    perfil = obter_ativo()
    cfg = perfil.config
    print(f"Perfil ativo: {perfil.nome}")

    barramento = BarramentoEventos()
    controlador = ControladorExecucao()

    def log(msg: str, nivel: str = "info") -> None:
        print(f"[bot] {msg}")
        barramento.publicar(LinhaRaciocinio(time.perf_counter(), 0, msg, nivel))

    # Sem calibração, NÃO subimos o loop — mas o painel sobe mesmo assim, para o
    # usuário calibrar e configurar no navegador e então reiniciar o bot.
    loop = None
    if cfg.regioes.calibrado:
        loop = _montar_loop(cfg, controlador, barramento, log)
        loop.start()
    else:
        log("Regiões de HP/Mana não calibradas — abra o portal e calibre, depois reinicie o bot.", "alerta")

    app = criar_app(barramento, controlador)
    print(f"\nPortal ao vivo: http://{cfg.painel.host}:{cfg.painel.port}\n")

    import uvicorn

    try:
        uvicorn.run(app, host=cfg.painel.host, port=cfg.painel.port, log_level="warning")
    finally:
        controlador.definir(EstadoExecucao.PARADO)
        if loop is not None:
            loop.join(timeout=2.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
