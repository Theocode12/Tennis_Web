import logging
from configparser import ConfigParser
from functools import lru_cache
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends

from db.redis_storage import RedisStorageSingleton
from utils.load_config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)
redis_store: RedisStorageSingleton | None = None


@lru_cache
def get_app_config() -> ConfigParser:
    try:
        config = load_config()
    except Exception as e:
        logger.exception(f"Error loading config: {e}")
        raise
    return config


async def init_redis() -> None:
    global redis_store
    config = get_app_config()
    redis_store = RedisStorageSingleton(config)
    await redis_store.connect()


async def close_redis() -> None:
    if redis_store:
        await redis_store.close()


def get_redis_client() -> redis.Redis:
    if not redis_store:
        raise RuntimeError("Redis not initialized")
    return redis_store.get_client()


@lru_cache
def get_app_logger(
    config: Annotated[ConfigParser, Depends(get_app_config)],
) -> logging.Logger:
    try:
        app_logger = get_logger(__name__, config)
    except Exception as e:
        logger.exception(f"Error creating logger: {e}")
        raise

    return app_logger
