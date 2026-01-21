from contextlib import asynccontextmanager

from app.dependencies import close_redis, init_redis


@asynccontextmanager
async def redis_lifespan(app):
    await init_redis()
    try:
        yield
    finally:
        await close_redis()
