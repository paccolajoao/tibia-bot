"""Teste da ponte assíncrona: produtor (thread) -> consumidor (asyncio) -> broadcast."""

from __future__ import annotations

import asyncio

from bot.painel.ponte import PonteAssincrona
from bot.telemetria import eventos as ev
from bot.telemetria.barramento import BarramentoEventos


class FakeWS:
    def __init__(self):
        self.msgs = []

    async def send_json(self, m):
        self.msgs.append(m)


async def test_ponte_faz_broadcast():
    bus = BarramentoEventos()
    clientes = set()
    ws = FakeWS()
    clientes.add(ws)
    loop = asyncio.get_running_loop()

    ponte = PonteAssincrona(bus.obter_fila(), clientes, loop)
    tarefa = asyncio.create_task(ponte.executar())

    bus.publicar(ev.LinhaRaciocinio(0.0, 1, "oi", "info"))
    bus.publicar(ev.LinhaRaciocinio(0.0, 2, "tchau", "info"))
    await asyncio.sleep(0.3)

    ponte.parar()
    tarefa.cancel()
    try:
        await tarefa
    except asyncio.CancelledError:
        pass

    textos = [m.get("texto") for m in ws.msgs]
    assert "oi" in textos
    assert "tchau" in textos
