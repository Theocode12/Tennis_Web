from .base_storage import BaseStorage


class RedisStorage(BaseStorage):
    def __init__(self, redis_client):
        self.redis = redis_client

    async def save_result(self, game_id, data):
        self.redis.set(game_id, data)