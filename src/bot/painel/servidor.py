"""Servidor FastAPI do painel: serve o frontend e o WebSocket de telemetria.

- GET /         -> index.html
- /static/*     -> CSS/JS
- WS /ws        -> recebe snapshot inicial + stream de eventos; aceita comandos
                   {cmd: pausar|retomar|parar} de volta (canal de controle).
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bot.nucleo.estado_execucao import ControladorExecucao, EstadoExecucao
from bot.painel.ponte import PonteAssincrona

DIR_WEB = Path(__file__).parent / "web"

_COMANDOS = {
    "pausar": EstadoExecucao.PAUSADO,
    "retomar": EstadoExecucao.RODANDO,
    "parar": EstadoExecucao.PARADO,
}


def criar_app(barramento, controlador: ControladorExecucao) -> FastAPI:
    clientes: set[WebSocket] = set()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        ponte = PonteAssincrona(barramento.obter_fila(), clientes, loop)
        tarefa = asyncio.create_task(ponte.executar())
        try:
            yield
        finally:
            ponte.parar()
            tarefa.cancel()

    app = FastAPI(title="Bot Tibia — Painel", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(DIR_WEB)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(DIR_WEB / "index.html"))

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        clientes.add(websocket)
        snap = barramento.ultimo_snapshot()
        if snap is not None:
            try:
                await websocket.send_json(snap.to_dict())
            except Exception:
                pass
        try:
            while True:
                msg = await websocket.receive_json()
                estado = _COMANDOS.get(msg.get("cmd"))
                if estado is not None:
                    controlador.definir(estado)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            clientes.discard(websocket)

    return app
