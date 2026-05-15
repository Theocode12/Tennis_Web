from redis import Redis

from utils.load_config import load_config


def get_redis_client() -> Redis:
    config = load_config()
    return Redis(
        host=config.get("app", "redisHost", fallback="localhost"),
        port=config.getint("app", "redisPort", fallback=6379),
        decode_responses=True,
    )
