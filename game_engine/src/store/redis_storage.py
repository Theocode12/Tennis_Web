from .base_storage import BaseStorage
from dataclasses import asdict
import redis.asyncio as aioredis
import json


class RedisStorage(BaseStorage):
    def __init__(self, url="redis://localhost"):
        self.redis = aioredis.from_url(
            url,
            max_connections=20,
            decode_responses=False
        )

    def get_prefixed_id(game_id: str) -> str:
        return f'lt_{game_id}'

    async def store_game_data(self, data):
        """Atomic single-command write - no lock needed"""
        await self.redis.hset(
            f"{data.game_id}:metadata",
            mapping={k: json.dumps(v) for k, v in asdict(data).items()}
        )

    async def append_score(self, game_id, score_data):
        """Atomic list append - no lock needed"""
        await self.redis.rpush(
            f"{game_id}:scores",
            json.dumps(score_data)
        )