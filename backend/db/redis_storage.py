from __future__ import annotations

import configparser
from logging import Logger

import redis.asyncio as redis

from app.shared.lib.singleton_metaclass import SingletonMeta
from db.exceptions.redis_connection_error import RedisConnectionError
from utils.logger import get_logger  # Adjust import path to fit your structure


class RedisStorageBase:
    """
    Manages a singleton Redis connection pool for backend operations.

    Ensures a shared connection pool for all Redis interactions, with built-in
    connection validation and optional logger support.
    """

    def __init__(
        self, config: configparser.ConfigParser, logger: Logger | None = None
    ) -> None:
        """
        Initialize the Redis storage manager.

        Args:
            config (ConfigParser): Application configuration containing
                                    storage settings.
            logger (Optional[Logger]): Optional logger instance. If not provided,
                a default logger is retrieved using `get_logger()`.
        """
        self.url = config.get("app", "redisUrl", fallback="redis://localhost")
        self.pool: redis.ConnectionPool | None = None
        self.logger = logger or get_logger(self.__class__.__name__)

    async def connect(self) -> None:
        """
        Initialize the Redis connection pool and validate connectivity.

        This method is idempotent; it only creates the pool if one doesn't
        already exist.

        Raises:
            RedisConnectionError: If Redis server is unreachable or ping fails.
        """
        if self.pool is None:
            self.logger.debug("Initializing Redis connection pool.")
            self.pool = redis.ConnectionPool.from_url(
                self.url,
                decode_responses=True,
                socket_keepalive=True,
                health_check_interval=30,
                retry_on_timeout=True,
            )

        try:
            async with redis.Redis(connection_pool=self.pool) as client:
                if await client.ping():
                    self.logger.info("Redis connection established successfully.")
                else:
                    self.logger.error("Redis ping failed.")
                    raise RedisConnectionError("Redis ping failed.")
        except Exception as e:
            self.logger.exception(f"Redis connection failed: {e}")
            raise RedisConnectionError(f"Redis connection failed: {e}") from e

    def get_client(self) -> redis.Redis:
        """
        Retrieve a Redis client using the shared connection pool.

        Returns:
            redis.Redis: Redis client instance.

        Raises:
            RuntimeError: If the connection pool has not been initialized.
        """
        if self.pool is None:
            error_msg = "Redis connection pool is not initialized. \
                         Did you forget to call connect()?"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.logger.debug("Returning Redis client instance from pool.")
        return redis.Redis(connection_pool=self.pool)

    async def close(self) -> None:
        """
        Clean up and close the Redis connection pool.
        """
        if self.pool:
            self.logger.info("Closing Redis connection pool.")
            await self.pool.aclose()
            self.logger.debug("Redis pool closed.")


class RedisStorageSingleton(RedisStorageBase, metaclass=SingletonMeta):
    pass
