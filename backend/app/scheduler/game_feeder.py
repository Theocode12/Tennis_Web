from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import AsyncGenerator, Awaitable
from logging import Logger
from pathlib import Path
from typing import Any, cast

import redis.asyncio as redis
from db.file_storage import BackendFileStorage
from db.redis_storage import BackendRedisStorage
from utils.logger import get_logger


class BaseGameFeeder(ABC):
    """
    Abstract base class for game feeders that use batched in-memory caching.

    Concrete implementations must provide logic for loading game details
    and score batches from a specific storage backend.
    """

    batch_size: int
    _buffer: deque[Any]
    _exhausted: bool
    logger: Logger

    def __init__(
        self, game_id: str, batch_size: int = 30, logger: Logger | None = None
    ) -> None:
        """
        Initialize the game feeder with batching support.

        Args:
            game_id (str): Unique identifier for the game.
            batch_size (int): Number of score entries to fetch per batch.
        """
        self.game_id: str = game_id
        self.batch_size = batch_size
        self._buffer = deque()
        self._exhausted = False
        self.logger = logger or get_logger(self.__class__.__name__)

    @abstractmethod
    async def _load_batch(self) -> list[Any]:
        """
        Load the next batch of score entries from the data source.

        Returns:
            list[Any]: List of score data objects.
        """
        pass

    @abstractmethod
    async def get_game_details(self) -> dict[str, Any]:
        """
        Retrieve game metadata such as game ID and team information.

        Returns:
            dict[str, Any]: Game metadata dictionary.
        """
        pass

    async def get_next_score(self) -> AsyncGenerator[Any, None]:
        """
        Asynchronously yield score entries one at a time.

        Fetches new batches when the internal buffer is exhausted.

        Yields:
            Any: A single score entry from the batch.
        """
        while not self._exhausted or self._buffer:
            if not self._exhausted:
                await self._refill_buffer()

            if self._buffer:
                yield self._buffer.popleft()

    async def _refill_buffer(self) -> None:
        """
        Load a new batch of scores into the internal buffer.

        Sets the `_exhausted` flag if no more data is available.
        """
        if self._exhausted:
            return

        new_batch = await self._load_batch()

        if not new_batch:
            self._exhausted = True
            if hasattr(self, "logger"):
                self.logger.debug(f"No more data to load for game_id={self.game_id}")
            return

        self._buffer.extend(new_batch)
        if hasattr(self, "logger"):
            self.logger.debug(
                f"Loaded batch of {len(new_batch)} scores for game_id={self.game_id}"
            )

    async def cleanup(self) -> None:
        """
        Clear the internal score buffer.

        Can be used to release memory after processing.
        """
        self._buffer.clear()


class RedisGameFeeder(BaseGameFeeder):
    """
    Game data feeder that reads game information and scores from Redis.

    This feeder pulls data from Redis using a shared connection pool and supports
    batched score loading.
    """

    def __init__(
        self,
        game_id: str,
        storage: BackendRedisStorage,
        batch_size: int = 30,
        logger: Logger | None = None,
    ) -> None:
        """
        Initialize the Redis-based game feeder.

        Args:
            game_id (str): Unique identifier for the game.
            storage (BackendRedisStorage): Redis connection manager.
            batch_size (int): Number of score entries to load per batch.
            logger (Optional[Logger]): Optional logger instance.
                Defaults to a logger retrieved using `get_logger()`.
        """
        super().__init__(game_id, batch_size, logger)
        self.storage = storage
        self.score_key = f"{self.game_id}:scores"
        self.cursor = 0
        self._game_details: dict[str, Any] | None = None

    async def get_game_details(self) -> dict[str, Any]:
        """
        Retrieve basic game details stored in Redis.

        Returns:
            dict[str, Any]: Dictionary with 'game_id' and 'teams'.

        Raises:
            KeyError: If expected fields are missing.
            json.JSONDecodeError: If the Redis value is malformed.
        """
        if self._game_details is None:
            try:
                async with self.storage.get_client() as client:
                    raw_data = await client.get(self.game_id)
                    if raw_data is None:
                        self.logger.warning(
                            f"No game metadata found for ID: {self.game_id}"
                        )
                        raise KeyError(
                            f"Missing metadata for game_id={self.game_id}"
                        )

                    data = json.loads(raw_data)

                self._game_details = {
                    "game_id": data["game_id"],
                    "teams": data["teams"],
                }
                self.logger.debug(f"Game details loaded for game_id={self.game_id}")

            except (json.JSONDecodeError, KeyError) as e:
                self.logger.exception(
                    f"Failed to retrieve game details from Redis: {e}"
                )
                raise

        return self._game_details

    async def _ensure_connected(self) -> None:
        """
        Ensure Redis connection pool is initialized.
        """
        if not self.storage.pool:
            self.logger.debug("Establishing Redis connection...")
            await self.storage.connect()

    async def _get_length(self, client: redis.Redis, key: str) -> int:
        """
        Get the number of items in the Redis list for the given key.

        Args:
            client (redis.Redis): Redis client instance.
            key (str): Redis list key.

        Returns:
            int: Length of the list.
        """
        raw = client.llen(key)
        return await cast(Awaitable[int], raw)

    async def _get_batch(
        self, client: redis.Redis, start: int, end: int
    ) -> list[str]:
        """
        Retrieve a batch of score entries from Redis.

        Args:
            client (redis.Redis): Redis client instance.
            start (int): Start index for the Redis list.
            end (int): End index for the Redis list.

        Returns:
            list[str]: List of raw JSON strings representing scores.
        """
        raw = client.lrange(self.score_key, start, end)
        return await cast(Awaitable[list[str]], raw)

    async def _load_batch(self) -> list[Any]:
        """
        Load a batch of score entries from Redis.

        Returns:
            list[Any]: List of parsed score objects.

        Raises:
            json.JSONDecodeError: If score entries cannot be parsed.
        """
        await self._ensure_connected()

        async with self.storage.get_client() as client:
            list_length = await self._get_length(client, self.score_key)

            if self.cursor >= list_length:
                self.logger.debug(
                    f"No more scores to load for game_id={self.game_id}"
                )
                return []

            batch = await self._get_batch(
                client, self.cursor, self.cursor + self.batch_size - 1
            )
            self.cursor += len(batch)

            try:
                parsed_batch = [json.loads(score) for score in batch]
                self.logger.debug(
                    f"Loaded score batch of size {len(parsed_batch)} "
                    f"for game_id={self.game_id}"
                )
                return parsed_batch
            except json.JSONDecodeError:
                self.logger.exception(
                    f"Error decoding score batch for game_id={self.game_id}"
                )
                raise


class FileGameFeeder(BaseGameFeeder):
    """
    Game data feeder that reads game information and scores from a JSON file.

    This class loads data on-demand using a file-based storage backend.
    """

    def __init__(
        self,
        game_id: str,
        storage: BackendFileStorage,
        logger: Logger | None = None,
    ) -> None:
        """
        Initialize the file-based game feeder.

        Args:
            game_id (str): Unique identifier for the game.
            storage (BackendFileStorage): File storage manager to resolve file paths.
            logger (Optional[Logger]): Optional logger instance.
                Defaults to a logger retrieved using `get_logger()`.
        """
        super().__init__(game_id=game_id, logger=logger)
        self.storage = storage
        self.file_path = self.storage.get_game_path(game_id)
        self._game_details: dict[str, Any] | None = None

    async def get_game_details(self) -> dict[str, Any]:
        """
        Retrieve game metadata such as game ID and team info.

        Returns:
            dict[str, Any]: Dictionary containing 'game_id' and 'teams'.

        Raises:
            FileNotFoundError: If the game file does not exist.
            json.JSONDecodeError: If the file contents are not valid JSON.
            KeyError: If expected keys are missing from the JSON.
        """
        if self._game_details is None:
            if Path(self.file_path).is_file():
                try:
                    with open(self.file_path, encoding="utf-8") as f:
                        data: dict[str, Any] = json.load(f)

                    self._game_details = {
                        "game_id": data["game_id"],
                        "teams": data["teams"],
                    }

                    self.logger.debug(
                        f"Loaded game details for game_id={self.game_id}"
                    )

                except (json.JSONDecodeError, KeyError):
                    self.logger.exception(
                        f"Error parsing game file: {self.file_path}"
                    )
                    raise

            else:
                self.logger.error(f"Game file not found: {self.file_path}")
                raise FileNotFoundError(f"Game file not found: {self.file_path}")

        return self._game_details

    async def _load_batch(self) -> list[Any]:
        """
        Load all score entries from the game file.

        Returns:
            list[Any]: List of score data entries.

        Raises:
            FileNotFoundError: If the game file is not found.
            json.JSONDecodeError: If the file contents are invalid.
        """
        if Path(self.file_path).is_file():
            try:
                with open(self.file_path, encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)
                self.logger.debug(f"Loaded score batch for game_id={self.game_id}")
            except json.JSONDecodeError:
                self.logger.exception(
                    f"Failed to parse score data: {self.file_path}"
                )
                raise
        else:
            self._exhausted = True
            self.logger.error(f"Game file not found: {self.file_path}")
            raise FileNotFoundError(f"Game file not found: {self.file_path}")

        self._exhausted = True  # All data loaded at once
        return cast(list[Any], data.get("scores", []))
