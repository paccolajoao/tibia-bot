"""Ponte assíncrona: drena a queue do barramento (thread do bot) e faz broadcast
por WebSocket. É o lado consumidor da ponte thread<->async.

`run_in_executor(None, fila.get)` adapta o `.get()` bloqueante a `await` sem
travar o event loop. Usa timeout para que o shutdown seja responsivo.
"""

from __future__ import annotations

import asyncio
import queue
from typing import Any


class PonteAssincrona:
    def __init__(self, fila: queue.Queue, clientes: set[Any], loop: asyncio.AbstractEventLoop):
        self.fila = fila
        self.clientes = clientes
        self.loop = loop
        self._rodando = False

    async def executar(self) -> None:
        self._rodando = True
        while self._rodando:
            evento = await self.loop.run_in_executor(None, self._proximo)
            if evento is None:
                continue
            await self._broadcast(evento.to_dict())

    def parar(self) -> None:
        self._rodando = False

    def _proximo(self):
        try:
            return self.fila.get(timeout=0.5)
        except queue.Empty:
            return None

    async def _broadcast(self, mensagem: dict) -> None:
        mortos = []
        for ws in list(self.clientes):
            try:
                await ws.send_json(mensagem)
            except Exception:
                mortos.append(ws)
        for ws in mortos:
            self.clientes.discard(ws)
