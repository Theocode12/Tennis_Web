import aioredis
from .message_broker import MessageBroker
from typing import Any, AsyncIterator
import json
from contextlib import asynccontextmanager

# TO BE FIXED
class RedisMessageBroker(MessageBroker):
    def __init__(self, redis_url="redis://localhost"):
        self.redis_url = redis_url
        self.redis = None
        self.pubsub = None

    async def connect(self):
        self.redis = await aioredis.from_url(self.redis_url)
        self.pubsub = self.redis.pubsub()

    async def publish(self, game_id: str, channel: str, message: Any) -> int:
        full_channel = f"{game_id}:{channel}"
        return await self.redis.publish(full_channel, json.dumps(message))

    @asynccontextmanager
    async def subscribe(self, game_id: str, channel: str) -> AsyncIterator[AsyncIterator[Any]]:
        full_channel = f"{game_id}:{channel}"
        await self.pubsub.subscribe(full_channel)
        
        try:
            async def message_generator():
                async for message in self.pubsub.listen():
                    if message["type"] == "message":
                        yield json.loads(message["data"])
            
            yield message_generator()
        finally:
            await self.pubsub.unsubscribe(full_channel)

    async def broadcast(self, channel: str, message: Any) -> int:
        # Use Redis pattern matching
        return await self.redis.publish(f"*:{channel}", json.dumps(message))

    async def shutdown(self):
        if self.redis:
            await self.redis.close()