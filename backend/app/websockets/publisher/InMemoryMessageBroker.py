from typing import AsyncIterator, Set, List, Any
import asyncio
from collections import defaultdict
from .message_broker import MessageBroker

class InMemoryMessageBroker(MessageBroker):
    def __init__(self):
        self._subscribers = defaultdict(lambda: defaultdict(set))
        self._shutdown = asyncio.Event()  # Thread-safe shutdown signal

    async def publish(self, game_id: str, channel: str, message: Any) -> int:
        if self._shutdown.is_set():
            return 0
            
        subscribers = self._subscribers[game_id][channel]
        if not subscribers:
            return 0
            
        # Batch the puts to improve throughput
        tasks = [q.put(message) for q in list(subscribers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return len([r for r in results if not isinstance(r, Exception)])

    def subscribe(self, game_id: str, channel: str) -> AsyncIterator[Any]:
        queue = asyncio.Queue(maxsize=100)  # Prevent memory explosion
        self._subscribers[game_id][channel].add(queue)

        async def generator():
            try:
                while not self._shutdown.is_set():
                    try:
                        message = await asyncio.wait_for(
                            queue.get(),
                            timeout=1.0  # Periodic shutdown check
                        )
                        if message is None:
                            break
                        yield message
                    except asyncio.TimeoutError:
                        continue
            finally:
                self._unsubscribe(game_id, channel, queue)

        return generator()

    def _unsubscribe(self, game_id: str, channel: str, queue: asyncio.Queue):
        self._subscribers[game_id][channel].discard(queue)
        # Clean up empty channels/games
        if not self._subscribers[game_id][channel]:
            del self._subscribers[game_id][channel]
        if not self._subscribers[game_id]:
            del self._subscribers[game_id]

    async def broadcast(self, channel: str, message: Any) -> int:
        """Broadcast to all subscribers of this channel across ALL games.
        Returns total number of subscribers notified."""
        if self._shutdown.is_set():
            return 0

        total = 0
        for game_id in list(self._subscribers.keys()):
            queues = self._subscribers[game_id][channel]
            if queues:
                for queue in list(queues):
                    await queue.put(message)
                total += len(queues)
        return total

    async def shutdown(self):
        self._shutdown.set()
        for game_channels in self._subscribers.values():
            for channel_queues in game_channels.values():
                for queue in channel_queues:
                    await queue.put(None)  # Sentinel value
                channel_queues.clear()
        self._subscribers.clear()