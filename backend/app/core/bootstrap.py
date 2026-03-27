import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.background.consumer import game_command_consumer
from app.core.media_lifecyle import media_lifespan
from app.core.redis_lifecycle import redis_lifespan
from app.core.streaming_lifecycle import realtime_lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with redis_lifespan(app), realtime_lifespan(app), media_lifespan(app):
        consumer_task = asyncio.create_task(game_command_consumer(app))
        app.state.consumer_task = consumer_task

        try:
            yield
        finally:
            consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await consumer_task
