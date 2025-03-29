from .base_storage import BaseStorage
from dataclasses import asdict
import aioredis

class RedisStorage(BaseStorage):
    def __init__(self, url="redis://localhost"):
        self.redis = aioredis.from_url(url)

    def get_prefixed_id(game_id: str) -> str:
        return f'tennis_{game_id}'

    async def store_game_data(self, data):
        prefixed_id = self.get_prefixed_id(data.game_id)

        await self.redis.hset(prefixed_id, mapping=asdict(data))

    async def append_score(self, game_id, score_data):
        """Appends score data to the 'scores' list inside the prefixed game namespace"""
        prefixed_id = self.get_prefixed_id(game_id)
        score_key = f"{prefixed_id}:scores"

        await self.redis.rpush(score_key, score_data)
