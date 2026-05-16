import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.background.consumer import game_command_consumer
from app.core.media_lifecyle import media_lifespan
from app.core.redis_lifecycle import redis_lifespan
from app.core.streaming_lifecycle import realtime_lifespan
from utils.logger import get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with redis_lifespan(app), realtime_lifespan(app), media_lifespan(app):
        await _recover_games_on_startup(app)

        consumer_task = asyncio.create_task(game_command_consumer(app))
        app.state.consumer_task = consumer_task

        try:
            yield
        finally:
            consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await consumer_task


async def _recover_games_on_startup(app: FastAPI) -> None:
    """
    Recover game schedulers that were running before the last shutdown/crash.
    """
    sio_context = getattr(app.state, "sio_context", None)
    if sio_context is None:
        get_logger().warning("Socket.IO context not available; skipping game recovery.")
        return

    scheduler_manager = sio_context.get_scheduler_manager()

    try:
        await scheduler_manager.recover_games()
    except Exception:
        get_logger().exception("Failed to recover game schedulers on startup")
