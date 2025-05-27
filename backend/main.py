from __future__ import annotations

import configparser
import logging

import socketio  # type: ignore
from fastapi import FastAPI
from utils.load_config import load_config
from utils.logger import get_logger

from app.websockets_api.socketio_server_context import SocketIOServerContext


def client_manager_factory(
    config: configparser.ConfigParser,
) -> socketio.AsyncManager:
    client_manager = config.get("app", "socketClientManger", fallback="manager")
    if client_manager == "redis":
        from socketio import AsyncRedisManager

        url = config.get("app", "redisUrl")
        return AsyncRedisManager(url)
    else:
        from socketio import AsyncManager

        return AsyncManager()


def bulid_socketio_server_context(
    sio: socketio.AsyncServer,
    config: configparser.ConfigParser,
    logger: logging.Logger,
) -> SocketIOServerContext:
    from app.broker.message_broker_factory import get_message_broker
    from app.core.ws_auth import AuthService
    from app.scheduler.manager import SchedulerManager
    from app.websockets_api.routes.router import Router

    broker = get_message_broker(config, logger)
    auth = AuthService()
    router = Router(logger=logger)
    scheduler_manager = SchedulerManager(broker, config=config, logger=logger)

    return SocketIOServerContext(
        sio=sio,
        broker=broker,
        auth=auth,
        router=router,
        scheduler_manager=scheduler_manager,
    )


config = load_config()
logger = get_logger(config=config)
client_manager = client_manager_factory(config)


sio = socketio.AsyncServer(
    client_manager, logger=True, cors_allowed_origins="*", async_mode="asgi"
)
sio_server_context = bulid_socketio_server_context(
    sio=sio, config=config, logger=logger
)
sio_server_context.register()

socket_app = socketio.ASGIApp(sio)
app = FastAPI()
app.mount("/", socket_app)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"Hello": "World"}
