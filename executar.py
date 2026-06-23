"""Entrypoint principal: sobe o loop do bot (thread) + o painel web (uvicorn).

Uso:  python executar.py   (de preferência num terminal como Administrador)
"""

from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from bot.captura.fabrica import criar_capturador  # noqa: E402
from bot.configuracao import carregar_config  # noqa: E402
from bot.contexto import Contexto  # noqa: E402
from bot.decisao.comportamentos.alvo import Alvo  # noqa: E402
from bot.decisao.comportamentos.auto_cura import AutoCura  # noqa: E402
from bot.decisao.comportamentos.comer import Comer  # noqa: E402
from bot.decisao.comportamentos.saque import Saque  # noqa: E402
from bot.decisao.cooldown import GerenciadorCooldown  # noqa: E402
from bot.decisao.motor import MotorDecisao  # noqa: E402
from bot.entrada.teclado_directinput import EntradaDirectInput  # noqa: E402
from bot.nucleo.estado_execucao import ControladorExecucao, EstadoExecucao  # noqa: E402
from bot.nucleo.loop_bot import LoopBot  # noqa: E402
from bot.nucleo.seguranca import Seguranca  # noqa: E402
from bot.painel.servidor import criar_app  # noqa: E402
from bot.telemetria.barramento import BarramentoEventos  # noqa: E402
from bot.telemetria.eventos import LinhaRaciocinio  # noqa: E402


def main() -> int:
    cfg = carregar_config()
    if not cfg.regioes.calibrado:
        print("Regiões de HP/Mana não calibradas.")
        print("Rode primeiro:  python calibrar.py")
        return 1

    barramento = BarramentoEventos()
    controlador = ControladorExecucao()

    def log(msg: str, nivel: str = "info") -> None:
        print(f"[bot] {msg}")
        barramento.publicar(LinhaRaciocinio(time.perf_counter(), 0, msg, nivel))

    capturador = criar_capturador(
        cfg.captura.backend,
        cfg.captura.monitor,
        log,
        tibia_screenshots=cfg.captura.tibia_screenshots,
        hotkey_screenshot=cfg.captura.hotkey_screenshot,
        fps_alvo=cfg.captura.fps_alvo,
        obs_device_index=cfg.captura.obs_device_index,
        obs_device_nome=cfg.captura.obs_device_nome,
    )
    entrada = EntradaDirectInput(cfg.entrada.atraso_pre_ms, cfg.entrada.atraso_pos_ms)
    cooldown = GerenciadorCooldown({**cfg.cura.cooldown_s, **cfg.alvo.cooldown_s})
    comportamentos = [AutoCura(cfg.cura, cfg.visao.confianca_minima)]
    if cfg.regioes.battle_list_calibrado:
        comportamentos.append(Alvo(cfg.alvo, cfg.visao.confianca_minima))
        log("Targeting habilitado (battle list calibrada)")
        if cfg.saque.ativo:
            comportamentos.append(Saque(cfg.saque))
            log(f"Auto-loot (Quick Loot) habilitado -> tecla {cfg.saque.tecla.upper()}")
    else:
        log("Targeting/auto-loot desligados — battle list não calibrada (rode calibrar.py)")
    if cfg.comer.ativo:
        comportamentos.append(Comer(cfg.comer))
        log(f"Auto-comer habilitado -> tecla {cfg.comer.tecla.upper()} a cada {cfg.comer.intervalo_s:.0f}s")
    motor = MotorDecisao(comportamentos, cooldown)
    seguranca = Seguranca(controlador, cfg.seguranca, log)
    seguranca.registrar_hotkeys()

    contexto = Contexto(config=cfg)
    loop = LoopBot(contexto, capturador, entrada, motor, controlador, seguranca, barramento)
    loop.start()

    app = criar_app(barramento, controlador)
    print(f"\nPainel ao vivo: http://{cfg.painel.host}:{cfg.painel.port}\n")

    import uvicorn

    try:
        uvicorn.run(app, host=cfg.painel.host, port=cfg.painel.port, log_level="warning")
    finally:
        controlador.definir(EstadoExecucao.PARADO)
        loop.join(timeout=2.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
