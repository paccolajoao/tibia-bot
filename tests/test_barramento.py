"""Testes do barramento de eventos (fila limitada + snapshot)."""

from __future__ import annotations

from bot.telemetria import eventos as ev
from bot.telemetria.barramento import BarramentoEventos


def test_descarta_mais_antigo_sem_travar():
    bus = BarramentoEventos(maxsize=3)
    for i in range(10):  # publica muito além da capacidade — não pode travar
        bus.publicar(ev.LinhaRaciocinio(0.0, i, f"m{i}", "info"))
    fila = bus.obter_fila()
    itens = []
    while not fila.empty():
        itens.append(fila.get_nowait())
    assert len(itens) <= 3
    assert itens[-1].tick == 9  # o evento mais novo sobrevive


def test_ultimo_snapshot():
    bus = BarramentoEventos()
    snap = ev.SnapshotEstado(0.0, 5, 50.0, 40.0, 1.0, 15.0, "RODANDO", True, "mss")
    bus.publicar(snap)
    assert bus.ultimo_snapshot().tick == 5
