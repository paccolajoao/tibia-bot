"""Barramento de eventos: hand-off thread-safe do bot (produtor síncrono) para o
dashboard (consumidor assíncrono).

Usa `queue.Queue` LIMITADA com `put_nowait` + descarte-do-mais-antigo se cheia:
o loop do bot NUNCA trava por causa de um painel lento/ausente — telemetria é
best-effort, a cadência do bot é sagrada.

Também guarda o último SnapshotEstado sob lock, para um cliente novo receber o
estado atual imediatamente ao conectar.
"""

from __future__ import annotations

import queue
import threading
from typing import Any

from bot.telemetria.eventos import SnapshotEstado


class BarramentoEventos:
    def __init__(self, maxsize: int = 256):
        self._fila: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()
        self._ultimo_snapshot: SnapshotEstado | None = None

    def publicar(self, evento: Any) -> None:
        if isinstance(evento, SnapshotEstado):
            with self._lock:
                self._ultimo_snapshot = evento
        try:
            self._fila.put_nowait(evento)
        except queue.Full:
            try:
                self._fila.get_nowait()  # descarta o mais antigo
            except queue.Empty:
                pass
            try:
                self._fila.put_nowait(evento)
            except queue.Full:
                pass

    def obter_fila(self) -> queue.Queue:
        return self._fila

    def ultimo_snapshot(self) -> SnapshotEstado | None:
        with self._lock:
            return self._ultimo_snapshot
