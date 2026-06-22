"""Smoke do painel web — serve o HTML e faz streaming por WebSocket, sem o jogo.

Usa o TestClient do Starlette (precisa de httpx, em requirements-dev). Prova que: a
página carrega com as seções novas (Detecção/stats), o cliente recebe o snapshot
inicial ao conectar, e os eventos publicados no barramento chegam pelo WebSocket
(incluindo `stats` com os contadores novos e `deteccao` com criaturas).
"""

from __future__ import annotations

import time

from starlette.testclient import TestClient

from bot.nucleo.estado_execucao import ControladorExecucao, EstadoExecucao
from bot.painel.servidor import criar_app
from bot.telemetria.barramento import BarramentoEventos
from bot.telemetria.eventos import EventoDeteccao, EventoStats, SnapshotEstado


def _snapshot():
    return SnapshotEstado(
        ts=0.0,
        tick=1,
        hp_pct=80.0,
        mana_pct=70.0,
        hp_confianca=1.0,
        fps=15.0,
        estado_execucao="RODANDO",
        janela_focada=True,
        backend_captura="mss",
    )


def test_index_serve_secoes_novas():
    app = criar_app(BarramentoEventos(), ControladorExecucao())
    with TestClient(app) as client:
        r = client.get("/")
        assert r.status_code == 200
        for marcador in ("Detec", "st-ataques", "st-refeicoes", "st-saques", "det-criaturas"):
            assert marcador in r.text


def test_ws_entrega_snapshot_e_eventos():
    bus = BarramentoEventos()
    bus.publicar(_snapshot())  # vira o "último snapshot" enviado ao conectar
    app = criar_app(bus, ControladorExecucao())
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        primeiro = ws.receive_json()  # snapshot inicial enviado ao conectar
        # publica DEPOIS de conectar: antes disso a ponte faria broadcast p/ ninguém
        bus.publicar(EventoStats(0.0, 5.0, 1, 2, 15.0, ataques=3, refeicoes=1, saques=2))
        bus.publicar(
            EventoDeteccao(0.0, 1, hp=None, mana=None, criaturas={"n": 2, "alvo_atual": False, "confianca": 0.9})
        )
        tipos: dict[str, dict] = {primeiro["tipo"]: primeiro}
        for _ in range(8):
            if {"estado", "stats", "deteccao"} <= tipos.keys():
                break
            msg = ws.receive_json()
            tipos[msg["tipo"]] = msg

    assert tipos["estado"]["hp_pct"] == 80.0
    assert tipos["stats"]["saques"] == 2 and tipos["stats"]["ataques"] == 3
    assert tipos["deteccao"]["criaturas"]["n"] == 2


def test_ws_comando_controla_o_bot():
    bus = BarramentoEventos()
    ctrl = ControladorExecucao()
    app = criar_app(bus, ctrl)
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"cmd": "pausar"})
        prazo = time.time() + 3.0
        while ctrl.atual() != EstadoExecucao.PAUSADO and time.time() < prazo:
            time.sleep(0.02)
    assert ctrl.atual() == EstadoExecucao.PAUSADO
