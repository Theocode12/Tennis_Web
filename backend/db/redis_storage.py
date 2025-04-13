import redis.asyncio as aioredis
import asyncio
from backend.app.shared.lib.singleton_metaclass import SingletonMeta


class BackendRedisStorage(metaclass=SingletonMeta):
    """Dedicated Redis connection pool for backend operations"""
    
    def __init__(self, url: str = "redis://localhost"):
        self._pool = None
        self.url = url
        self._lock = asyncio.Lock()

    async def connect(self):
        """Initialize connection pool"""
        self._pool = await aioredis.from_url(
            self.url,
            decode_responses=True,
            socket_keepalive=True,
            health_check_interval=30,
            retry_on_timeout=True,
        )

    def get_pool(self):
        """Get the connection pool"""
        if not self._pool:
            raise RuntimeError("Connection pool is not initialized.")
        return self._pool

    async def close(self):
        """Cleanup connections"""
        if self._pool:
            await self._pool.close()

