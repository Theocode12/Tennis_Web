from configparser import ConfigParser

import redis.asyncio as redis

from db.redis_storage import RedisStorageSingleton as RedisStorage


async def get_redis_client(config: ConfigParser) -> redis.Redis:
    try:
        redis_store = RedisStorage(config)
        await redis_store.connect()
        return redis_store.get_client()
    except Exception as e:
        raise RuntimeError(f"Error connecting to Redis: {e}") from e
