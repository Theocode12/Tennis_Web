import json
from logging import Logger
from typing import Any

from db.redis_storage import RedisStorageBase
from utils.logger import get_logger

from .game_state_key_builder import GameStateKeyBuilder


class RedisSchedulerStatePublisher:
    def __init__(
        self,
        storage: RedisStorageBase,
        *,
        ttl_seconds: int = 30,
        key_builder: GameStateKeyBuilder,
        logger: Logger | None = None,
    ) -> None:
        self.storage = storage
        self.ttl_seconds = ttl_seconds
        self.r_key = key_builder
        self.logger = logger or get_logger(self.__class__.__name__)

    async def publish_state(
        self,
        game_id: str,
        state: dict[str, Any],
    ) -> None:
        if not self.storage.is_connected():
            await self.storage.connect()

        try:
            await self.storage.get_client().set(
                self.r_key.key(game_id),
                json.dumps(state),
                ex=self.ttl_seconds,
            )
            self.logger.debug("Scheduler state published successfully")
        except Exception as e:
            self.logger.error(f"Error publishing scheduler state: {e}")
            raise

    async def cleanup(self, *, game_id: str) -> None:
        await self.storage.get_client().delete(self.r_key.key(game_id))
        self.logger.info("Scheduler state cleanup completed")
