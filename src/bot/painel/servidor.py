"""Servidor FastAPI do portal: API REST + frontend + WebSocket de telemetria.

- /api/*        -> API REST (perfis, config, regiões, calibração) — ver api.py
- WS /ws        -> snapshot inicial + stream de eventos; aceita comandos
                   {cmd: pausar|retomar|parar} de volta (canal de controle).
- /             -> SPA do portal (portal/dist) se buildado; senão cai no painel
                   vanilla legado (src/bot/painel/web) para não quebrar nada.

Em desenvolvimento, o frontend roda no Vite (porta 5173) com proxy de /api e /ws
para cá; em produção, `npm run build` gera portal/dist e o FastAPI o serve.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bot.configuracao import RAIZ_PROJETO
from bot.nucleo.estado_execucao import ControladorExecucao, EstadoExecucao
from bot.painel.api import criar_router_api
from bot.painel.ponte import PonteAssincrona

DIR_WEB_LEGADO = Path(__file__).parent / "web"
DIR_PORTAL = RAIZ_PROJETO / "portal" / "dist"

_COMANDOS = {
    "pausar": EstadoExecucao.PAUSADO,
    "retomar": EstadoExecucao.RODANDO,
    "parar": EstadoExecucao.PARADO,
}


def _portal_buildado() -> bool:
    return (DIR_PORTAL / "index.html").is_file()


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

    app = FastAPI(title="Bot Tibia — Portal", lifespan=lifespan)
    app.include_router(criar_router_api(barramento))

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

    _montar_frontend(app)
    return app


def _montar_frontend(app: FastAPI) -> None:
    """Serve a SPA do portal (se buildada) com fallback para qualquer rota; senão o painel legado."""
    if _portal_buildado():
        assets = DIR_PORTAL / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")
        indice = DIR_PORTAL / "index.html"

        @app.get("/")
        async def raiz():
            return FileResponse(str(indice))

        # SPA fallback: qualquer rota não-API/WS devolve o index (React Router cuida)
        @app.get("/{caminho:path}")
        async def spa(caminho: str):
            arquivo = DIR_PORTAL / caminho
            if arquivo.is_file():
                return FileResponse(str(arquivo))
            return FileResponse(str(indice))
        return

    # Fallback: painel vanilla legado enquanto o portal não foi buildado.
    app.mount("/static", StaticFiles(directory=str(DIR_WEB_LEGADO)), name="static")

    @app.get("/")
    async def index_legado():
        return FileResponse(str(DIR_WEB_LEGADO / "index.html"))
