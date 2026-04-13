import logging
import os
from configparser import ConfigParser
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request

from app.infra.music_file_store import MusicFileStore
from app.infra.music_redis_store import MusicRedisStore
from app.services.music_service import MusicService
from db.redis_storage import RedisStorageSingleton
from utils.load_config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Singletons
redis_store: RedisStorageSingleton | None = None
music_service_instance: MusicService | None = None

MEDIA_ROOT = Path("media")
MUSIC_STORE_PATH = Path("db/data/music.json")


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


def get_music_service() -> MusicService:
    global music_service_instance
    if music_service_instance:
        return music_service_instance

    redis_client = get_redis_client()
    file_store = MusicFileStore(MEDIA_ROOT, MUSIC_STORE_PATH)
    redis_store_obj = MusicRedisStore(redis_client)

    music_service_instance = MusicService(file_store, redis_store_obj)
    return music_service_instance


def get_app_logger(
    config: Annotated[ConfigParser, Depends(get_app_config)],
) -> logging.Logger:
    try:
        app_logger = get_logger(__name__, config)
    except Exception as e:
        logger.exception(f"Error creating logger: {e}")
        raise

    return app_logger


async def require_secret(request: Request) -> None:
    """
    Dependency that checks for a ``secret`` query parameter matching
    the ``API_SECRET`` environment variable.

    Returns 404 when the secret is missing or wrong — the endpoint
    simply doesn't exist for unauthenticated callers.
    """
    expected = os.environ.get("API_SECRET")
    if not expected:
        logger.error("API_SECRET not set")
        raise HTTPException(status_code=404, detail="Not found")

    provided = request.query_params.get("secret")
    if provided != expected:
        raise HTTPException(status_code=404, detail="Not found")
