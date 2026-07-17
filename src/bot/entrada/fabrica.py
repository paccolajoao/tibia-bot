"""Fábrica de entrada: escolhe o backend de teclado/mouse.

Ao contrário de `captura/fabrica.py`, não existe modo "auto" aqui — não há ambiguidade
de ambiente a resolver, o usuário escolhe explicitamente. Um backend não-default que
falhar ao iniciar levanta (sem cair silenciosamente para o SendInput: se o usuário
escolheu Arduino — geralmente por causa de elevação/anti-detecção — um fallback
silencioso pro SendInput anularia o motivo de ter escolhido o Arduino).
"""

from __future__ import annotations

from collections.abc import Callable

from bot.configuracao import ArduinoConfig
from bot.entrada.base import EntradaBase
from bot.entrada.teclado_directinput import EntradaDirectInput

Logger = Callable[[str], None]


def criar_entrada(
    backend: str,
    atraso_pre_ms: tuple[int, int] = (40, 90),
    atraso_pos_ms: tuple[int, int] = (30, 70),
    log: Logger | None = None,
    arduino: ArduinoConfig | None = None,
) -> EntradaBase:
    emitir = log or (lambda _msg: None)

    if backend == "directinput":
        entrada = EntradaDirectInput(atraso_pre_ms, atraso_pos_ms)
        emitir("Entrada: backend DirectInput (SendInput) ativo")
        return entrada

    if backend == "arduino":
        cfg_a = arduino or ArduinoConfig()
        try:
            from bot.entrada.teclado_arduino import EntradaArduino

            entrada = EntradaArduino(
                cfg_a.porta,
                cfg_a.baud_rate,
                cfg_a.timeout_s,
                cfg_a.largura_tela,
                cfg_a.altura_tela,
                atraso_pre_ms,
                atraso_pos_ms,
                log=emitir,
            )
            emitir(f"Entrada: backend Arduino ativo (porta {cfg_a.porta} @ {cfg_a.baud_rate} baud)")
            return entrada
        except Exception as e:
            raise RuntimeError(
                f"Backend arduino falhou: {e}. Confira a porta serial ({cfg_a.porta}), se o "
                "board está plugado e se entrada_hid.ino foi gravado nele "
                "(ver arduino/README.md) — a BlackBoard NÃO serve para isso."
            ) from e

    raise RuntimeError(f"Backend de entrada '{backend}' desconhecido. Use: directinput | arduino")
