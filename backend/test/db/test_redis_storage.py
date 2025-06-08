from __future__ import annotations

import logging
from configparser import ConfigParser
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis

from db.exceptions.redis_connection_error import RedisConnectionError
from db.redis_storage import RedisStorageBase as RedisStorage


@pytest.mark.asyncio
async def test_live_connect_success(
    is_redis_live: bool,
    valid_config: ConfigParser,
    dummy_logger: logging.Logger,
) -> None:
    if not is_redis_live:
        pytest.skip("Skipping test: Redis not running.")

    storage = RedisStorage(valid_config, dummy_logger)
    await storage.connect()
    assert storage.pool is not None
    await storage.close()


@pytest.mark.asyncio
async def test_live_get_client(
    is_redis_live: bool,
    valid_config: ConfigParser,
    dummy_logger: logging.Logger,
) -> None:
    if not is_redis_live:
        pytest.skip("Skipping test: Redis not running.")

    storage = RedisStorage(valid_config, dummy_logger)
    await storage.connect()
    async with storage.get_client() as client:
        assert isinstance(client, redis.Redis), (
            "Expected client to be a redis.Redis instance"
        )
    await storage.close()


@pytest.mark.asyncio
@patch("db.redis_storage.redis.Redis")
@patch("db.redis_storage.redis.ConnectionPool.from_url")
async def test_connect_success(
    mock_connection_from_url: MagicMock,
    mock_redis: redis.Redis,
    valid_config: ConfigParser,
    dummy_logger: logging.Logger,
) -> None:
    mock_pool = AsyncMock()
    mock_connection_from_url.return_value = mock_pool
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    mock_redis.return_value.__aenter__.return_value = mock_client  # type: ignore

    storage = RedisStorage(valid_config, dummy_logger)
    await storage.connect()

    assert storage.pool is not None
    assert mock_pool is storage.pool
    mock_client.ping.assert_awaited_once()


@pytest.mark.asyncio
@patch("db.redis_storage.redis.Redis")
@patch("db.redis_storage.redis.ConnectionPool.from_url")
async def test_connect_failure_ping(
    mock_connection_from_url: MagicMock,
    mock_redis: redis.Redis,
    valid_config: ConfigParser,
    dummy_logger: logging.Logger,
) -> None:
    mock_client = AsyncMock()
    mock_client.ping.return_value = False
    mock_redis.return_value.__aenter__.return_value = mock_client  # type: ignore

    storage = RedisStorage(valid_config, dummy_logger)

    with pytest.raises(RedisConnectionError, match="Redis ping failed"):
        await storage.connect()


@pytest.mark.asyncio
@patch("db.redis_storage.redis.Redis")
@patch("db.redis_storage.redis.ConnectionPool.from_url")
async def test_connect_exception(
    mock_connection_from_url: MagicMock,
    mock_redis: redis.Redis,
    valid_config: ConfigParser,
    dummy_logger: logging.Logger,
) -> None:
    mock_redis.return_value.__aenter__.side_effect = Exception("Connection refused")  # type: ignore

    storage = RedisStorage(valid_config, dummy_logger)

    with pytest.raises(RedisConnectionError, match="Redis connection failed"):
        await storage.connect()


def test_get_client_without_connect(
    valid_config: ConfigParser,
    dummy_logger: logging.Logger,
) -> None:
    storage = RedisStorage(valid_config, dummy_logger)
    with pytest.raises(
        RuntimeError, match="Redis connection pool is not initialized"
    ):
        storage.get_client()


@patch("db.redis_storage.redis.Redis")
def test_get_client_after_connect(
    mock_redis: redis.Redis,
    valid_config: ConfigParser,
    dummy_logger: logging.Logger,
) -> None:
    mock_pool = MagicMock()
    storage = RedisStorage(valid_config, dummy_logger)
    storage.pool = mock_pool

    client = storage.get_client()

    mock_redis.assert_called_once_with(connection_pool=mock_pool)  # type: ignore
    assert client is mock_redis.return_value  # type: ignore


@pytest.mark.asyncio
@patch("db.redis_storage.redis.ConnectionPool")
async def test_close_connection(
    mock_connection_from_url: MagicMock,
    valid_config: ConfigParser,
    dummy_logger: logging.Logger,
) -> None:
    mock_pool = AsyncMock()
    storage = RedisStorage(valid_config, dummy_logger)
    storage.pool = mock_pool

    await storage.close()
    mock_pool.aclose.assert_awaited_once()
