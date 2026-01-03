from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI

from app.dependencies import close_redis, init_redis
from app.websockets_api.client_manager import client_manager_factory
from app.websockets_api.socketio_server_context import (
    SocketIOServerContext,
    bulid_socketio_server_context,
)
from utils.load_config import load_config
from utils.logger import get_logger


async def put_and_start_game_in_scheduler_manager(
    sio_context: SocketIOServerContext,
) -> None:
    game_id = "test_123"
    scheduler_manager = sio_context.context.scheduler_manager

    scheduler, _ = await scheduler_manager.create_or_get_scheduler(game_id)
    # await scheduler.run()
    # await scheduler.start()
    print(scheduler_manager._schedulers)


@asynccontextmanager
async def realtime_lifespan(app: FastAPI):
    config = load_config()
    logger = get_logger()

    # --- Socket.IO setup ---
    client_manager = client_manager_factory(config)

    sio: socketio.AsyncServer = app.state.sio
    sio.manager = client_manager
    client_manager.set_server(sio)

    assert sio.manager.server is sio

    # sio = socketio.AsyncServer(
    #     client_manager=client_manager,
    #     async_mode="asgi",
    #     cors_allowed_origins="*",
    #     logger=True,
    # )

    sio_context = bulid_socketio_server_context(
        sio=sio,
        config=config,
        logger=logger,
    )
    sio_context.register()
    await put_and_start_game_in_scheduler_manager(sio_context)

    app.state.sio_context = sio_context
    # socket_app = socketio.ASGIApp(sio)

    # Store in FastAPI state
    # app.state.sio = sio
    # app.state.sio_context = sio_context
    # app.state.socket_app = socket_app

    try:
        yield
    finally:
        if sio_context is not None:
            logger.info("Shutting down Socket.IO context...")
            await sio_context.shutdown()


@asynccontextmanager
async def redis_lifespan(app: FastAPI):
    await init_redis()
    try:
        yield
    finally:
        await close_redis()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with redis_lifespan(app), realtime_lifespan(app):
        yield
