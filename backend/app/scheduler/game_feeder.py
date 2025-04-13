from db.redis_storage import BackendRedisStorage
from db.file_storage import BackendFileStorage
from abc import ABC, abstractmethod
import asyncio
from collections import deque
from typing import AsyncIterator, Any, Deque, List
import json
import os


class BaseGameFeeder(ABC):
    """Game feeder with batched in-memory caching"""

    batch_size: int
    _buffer: Deque[Any] # Type hint for the deque
    _exhausted: bool

    def __init__(self, batch_size: int = 30) -> None:
        self.batch_size = batch_size
        self._buffer = deque()
        self._exhausted = False

    @abstractmethod
    async def _load_batch(self) -> List[Any]:
        """Load next batch of scores from storage"""
        pass

    @abstractmethod
    async def get_metadata(self) -> dict:
        """Load next batch of scores from storage"""
        pass

    async def get_next_score(self) -> AsyncIterator[Any]:
        """Yield scores with batched loading"""
        while (not self._exhausted) or (self._buffer):
            if not self._exhausted: 
                await self._refill_buffer()
        
            yield self._buffer.popleft()

    async def _refill_buffer(self) -> None: # Return type hint
        """Load new batch into memory buffer"""
        if self._exhausted:
            return

        new_batch = await self._load_batch()
        # If _load_batch returns an empty list, it signifies the end
        if not new_batch:
            self._exhausted = True
            return

        self._buffer.extend(new_batch)

    async def cleanup(self):
        self._buffer.clear()


class RedisGameFeeder(BaseGameFeeder):
    def __init__(self, game_id: str, storage: BackendRedisStorage ,batch_size: int = 30):
        super().__init__(batch_size)
        self.storage = storage
        self.game_id = game_id
        self.score_key = f"{self.game_id}:scores"
        self.cursor = 0
        self._connection_lock = asyncio.Lock()
        self.metadata = None

    async def get_metadata(self):
        if self.metadata is None:
            async with self.storage.get_pool().client() as client:
                self.metadata = client.get(self.game_id)
        return self.metadata

    async def _ensure_connected(self):
        """Lazy connection initialization"""
        async with self._connection_lock:
            if not self.storage._pool:
                await self.storage.connect()
    
    async def _load_batch(self) -> list[Any]:
        await self._ensure_connected()
        
        async with self.storage.get_pool().client() as client:
            if self.cursor >= await client.llen(self.score_key):
                return []
            
            batch = await client.lrange(
                self.score_key,
                self.cursor,
                self.cursor + self.batch_size - 1
            )
            self.cursor += len(batch)
            return [json.loads(score) for score in batch]

class FileGameFeeder(BaseGameFeeder):
    def __init__(self, game_id: str, storage: BackendFileStorage):
        super().__init__()
        self.storage = storage
        self.game_id = game_id
        self.file_path = self.storage.get_game_path(game_id)
        self.metadata = None

    async def get_metadata(self):
        if self.metadata is None:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r") as f:
                    data = dict(json.load(f))
                self.metadata = data.pop('scores')
        return self.metadata

    async def _load_batch(self) -> list[Any]:
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                data = json.load(f)
                self._buffer = deque(data.get("scores", []))
        else:
            self._exhausted = True
            raise FileNotFoundError(f"Game file not found: {self.file_path}")
        self._exhausted = True  # File data loaded all at once

