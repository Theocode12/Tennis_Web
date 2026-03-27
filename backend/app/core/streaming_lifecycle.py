from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI

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
    game_id = "aa917483-8acc-43b5-beda-6e8f5b961e01"
    scheduler_manager = sio_context.context.scheduler_manager

    scheduler1, _ = await scheduler_manager.create_or_get_scheduler(game_id)
    scheduler2, _ = await scheduler_manager.create_or_get_scheduler("e6dbc235-3e1e-4e5d-9a82-536efc17a37a")
    await scheduler1.start()
    await scheduler2.start()
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

    sio_context = bulid_socketio_server_context(
        sio=sio,
        config=config,
        logger=logger,
    )
    sio_context.register()
    # await put_and_start_game_in_scheduler_manager(sio_context)

    app.state.sio_context = sio_context

    try:
        yield
    finally:
        if sio_context is not None:
            logger.info("Shutting down Socket.IO context...")
            await sio_context.shutdown()
