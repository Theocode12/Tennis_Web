from typing import AsyncIterator, Set, List, Any, Union
import asyncio
from collections import defaultdict
import logging
from app.broker.message_broker import MessageBroker


logger = logging.getLogger(__name__)

class InMemoryMessageBroker(MessageBroker):
    def __init__(self):
        # _subscriber Structure: {game_id: {channel: {queue1, queue2, ...}}}
        self._subscribers = defaultdict(lambda: defaultdict(set))
        self._shutdown = asyncio.Event()  # Thread-safe shutdown signal

    async def publish(self, game_id: str, channel: str, message: Any) -> int:
        """Publish message to specific game/channel. Returns number of queues notified."""
        if self._shutdown.is_set():
            return 0

        # Get the set of queues subscribed to this specific game_id and channel
        subscribers = self._subscribers.get(game_id, {}).get(channel, set())

        if not subscribers:
            return 0

        tasks = [q.put(message) for q in list(subscribers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful puts
        success_count = 0
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                queue_info = list(subscribers)[i] # Get corresponding queue for context
                logger.error(f"Error putting message on queue {queue_info} for {game_id}:{channel}: {r}", exc_info=r)
            else:
                success_count += 1

        return success_count
    

    def subscribe(self, game_id: str, channels: Union[str, List[str]]) -> AsyncIterator[Any]:
        """
        Subscribe to one or more channels for a specific game_id.

        Args:
            game_id: The ID of the game.
            channels: A single channel name (str) or a list of channel names (List[str]).

        Returns:
            An asynchronous iterator yielding messages from the subscribed channels.
        """
        if isinstance(channels, str):
            channels_list = [channels]
        elif not channels:
             async def empty_generator():
                 if False: yield # Never yield anything
             return empty_generator()
        else:
            channels_list = channels

        queue = asyncio.Queue(maxsize=100)
        logger.info(f"Creating subscription queue for {game_id=} on channels: {channels_list}")

        # Add this single queue to the subscriber set for EACH requested channel
        for channel in channels_list:
            self._subscribers[game_id][channel].add(queue)

        async def generator():
            active_channels = list(channels_list)
            try:
                while not self._shutdown.is_set():
                    try:
                        message = await asyncio.wait_for(
                            queue.get(),
                            timeout=1.0
                        )
                        # Check for sentinel value indicating shutdown or forced unsubscribe
                        if message is None:
                            break

                        yield message
                    except asyncio.TimeoutError:
                        # No message received within timeout, loop continues to check shutdown
                        continue
                    except asyncio.CancelledError:
                         raise
            finally:
                self._unsubscribe(game_id, active_channels, queue)

        return generator()

    def _unsubscribe(self, game_id: str, channels: List[str], queue: asyncio.Queue):
        """Remove a specific queue from the specified channels for a game_id."""
        game_data = self._subscribers.get(game_id)
        if not game_data:
            return

        for channel in channels:
            channel_subscribers = game_data.get(channel)
            if channel_subscribers:
                channel_subscribers.discard(queue)
                # If the channel set becomes empty, remove the channel entry
                if not channel_subscribers:
                    del game_data[channel]

        # If the game entry becomes empty (no channels left), remove the game entry
        if not game_data:
            self._subscribers.pop(game_id, None)

    async def broadcast(self, channel: str, message: Any) -> int:
        """Broadcast to all subscribers of this channel across ALL games."""
        if self._shutdown.is_set():
            return 0

        total_notified = 0
        tasks = []

        # Iterate safely over game IDs
        for game_id in list(self._subscribers.keys()):
            game_channels = self._subscribers.get(game_id)
            if game_channels:
                queues = game_channels.get(channel, set())
                if queues:
                    tasks.extend([q.put(message) for q in list(queues)])
                    total_notified += len(queues) # Count potential notifications

        if not tasks:
             return 0

        # Execute all puts concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log errors from broadcast puts
        error_count = 0
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Error during broadcast put to channel '{channel}': {r}", exc_info=r)
                error_count += 1

        actual_notified = total_notified - error_count
        logger.debug(f"Broadcast to channel '{channel}' potentially notified {total_notified} queues, {actual_notified} succeeded.")
        return actual_notified

    async def shutdown(self):
        """Gracefully shut down the broker."""
        if self._shutdown.is_set():
            return

        self._shutdown.set()

        # Collect all queues to send sentinel value
        all_queues: Set[asyncio.Queue] = set()
        for game_channels in self._subscribers.values():
            for channel_queues in game_channels.values():
                all_queues.update(channel_queues)

        # Send sentinel concurrently
        tasks = [q.put(None) for q in all_queues]
        await asyncio.gather(*tasks, return_exceptions=True) # Ignore errors here, just trying to notify

        # Clear internal state
        self._subscribers.clear()
