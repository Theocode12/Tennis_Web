from __future__ import annotations

import socketio

# from configparser import ConfigParser
from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.cors import setup_cors
from app.core.lifespan import lifespan

# from gameengine import GameCreationData
# from app.shared.lib.game_engine_config import CONFIG

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
)
socket_app = socketio.ASGIApp(sio)

app = FastAPI(lifespan=lifespan)

setup_cors(app)
app.state.sio = sio
app.state.socket_app = socket_app


app.include_router(v1_router)
app.mount("/", app.state.socket_app)
