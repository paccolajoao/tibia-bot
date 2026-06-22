"""Estado de execução + canal de controle painel->bot.

Separado da fila de telemetria (alta frequência, bot->painel). Comandos de
controle são raros e vão por aqui: enum sob Lock + Event para o loop esperar
barato quando pausado.
"""

from __future__ import annotations

import threading
from enum import Enum, auto


class EstadoExecucao(Enum):
    PARADO = auto()
    RODANDO = auto()
    PAUSADO = auto()
    PANICO = auto()


class ControladorExecucao:
    def __init__(self, inicial: EstadoExecucao = EstadoExecucao.RODANDO):
        self._estado = inicial
        self._lock = threading.Lock()
        self._evento_retomar = threading.Event()
        self._evento_retomar.set()  # não-pausado no início

    def definir(self, estado: EstadoExecucao) -> None:
        with self._lock:
            self._estado = estado
        if estado == EstadoExecucao.PAUSADO:
            self._evento_retomar.clear()
        else:
            self._evento_retomar.set()

    def atual(self) -> EstadoExecucao:
        with self._lock:
            return self._estado

    def alternar_pausa(self) -> None:
        atual = self.atual()
        if atual == EstadoExecucao.PAUSADO:
            self.definir(EstadoExecucao.RODANDO)
        elif atual == EstadoExecucao.RODANDO:
            self.definir(EstadoExecucao.PAUSADO)

    def aguardar_se_pausado(self, timeout: float = 0.2) -> None:
        """Bloqueia barato enquanto pausado, acordando periodicamente p/ checar parada."""
        self._evento_retomar.wait(timeout)
