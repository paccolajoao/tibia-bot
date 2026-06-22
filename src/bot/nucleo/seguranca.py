"""Segurança: hotkeys globais (pausar/pânico) + detecção de foco da janela.

Hotkeys globais usam a lib `keyboard` (requer admin). Se indisponível, o bot
ainda funciona — controla-se pelo painel.
"""

from __future__ import annotations

from collections.abc import Callable

from bot.configuracao import SegurancaConfig
from bot.nucleo.estado_execucao import ControladorExecucao, EstadoExecucao


class Seguranca:
    def __init__(
        self,
        controlador: ControladorExecucao,
        cfg: SegurancaConfig,
        log: Callable[[str], None] | None = None,
    ):
        self._ctrl = controlador
        self._cfg = cfg
        self._log = log or (lambda _msg: None)
        self._gw = None
        try:
            import pygetwindow as gw

            self._gw = gw
        except Exception as e:  # pragma: no cover
            self._log(f"Detecção de foco indisponível ({e}); bot não pausará por foco")

    def registrar_hotkeys(self) -> None:
        try:
            import keyboard
        except Exception as e:
            self._log(f"Hotkeys globais indisponíveis ({e}); use o painel para pausar/parar")
            return
        try:
            keyboard.add_hotkey(self._cfg.hotkey_pausar, self._on_pausar)
            keyboard.add_hotkey(self._cfg.hotkey_panico, self._on_panico)
        except Exception as e:  # falta de admin costuma estourar aqui
            self._log(f"Não foi possível registrar hotkeys ({e}); rode como Administrador")
            return
        self._log(
            f"Hotkeys: {self._cfg.hotkey_pausar.upper()}=pausar/retomar, "
            f"{self._cfg.hotkey_panico.upper()}=PÂNICO"
        )

    def _on_pausar(self) -> None:
        self._ctrl.alternar_pausa()

    def _on_panico(self) -> None:
        self._ctrl.definir(EstadoExecucao.PANICO)

    def janela_focada(self) -> bool:
        """True se a janela ativa contém o título configurado (ex.: 'Tibia').

        Em caso de falha de detecção, retorna True (não bloqueia o bot).
        """
        if self._gw is None:
            return True
        try:
            ativa = self._gw.getActiveWindow()
            titulo = (getattr(ativa, "title", "") or "")
            return self._cfg.titulo_janela_contains.lower() in titulo.lower()
        except Exception:
            return True
