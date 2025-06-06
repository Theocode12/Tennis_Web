from __future__ import annotations

import logging
from configparser import ConfigParser
from pathlib import Path

import pytest
import redis.asyncio as redis


@pytest.fixture(scope="module")
async def is_redis_live() -> bool:
    try:
        client = redis.Redis.from_url("redis://localhost:6379/0")
        pong = await client.ping()
        if not pong:
            return False

        await client.flushdb()
        return True
    except Exception:
        return False


@pytest.fixture
def dummy_logger() -> logging.Logger:
    logger = logging.getLogger("dummy")
    logger.addHandler(logging.NullHandler())
    return logger


@pytest.fixture
def valid_config(tmp_path: Path) -> ConfigParser:
    config = ConfigParser()
    config["app"] = {
        "gameFeeder": "file",
        "gameDataDir": str(tmp_path / "data" / "games"),
        "gameFileExt": ".json",
        "redisUrl": "redis://localhost:6379/0",
        "messageBroker": "memory",
        "defaultGameSpeed": "1",
        "pauseTimeoutSecs": "60",
        "socketClientManager": "manager",
    }
    return config
