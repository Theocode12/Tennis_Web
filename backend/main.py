from __future__ import annotations

import socketio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as v1_router
from app.core.bootstrap import lifespan
from app.core.cors import setup_cors

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
)
socket_app = socketio.ASGIApp(sio)

app = FastAPI(lifespan=lifespan)

app.mount("/media", StaticFiles(directory="media"), name="media")

setup_cors(app)
app.state.sio = sio
app.state.socket_app = socket_app


app.include_router(v1_router)
app.mount("/", app.state.socket_app)
