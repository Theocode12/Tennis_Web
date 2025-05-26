from __future__ import annotations

import asyncio
import configparser
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any

from app.broker.message_broker import MessageBroker
from app.shared.enums.broker_channels import BrokerChannels


class InMemoryMessageBroker(MessageBroker):
    """
    In-memory message broker using asyncio queues for lightweight pub/sub.
    Supports publishing, subscribing, and broadcasting messages within
    a single process.

    Subscribers are stored in a nested dictionary:
        {game_id: {channel: {queue1, queue2, ...}}}
    Example:
        self._subscribers["game123"]["score_update"] = {queue1, queue2}
    """

    def __init__(
        self,
        config: configparser.ConfigParser | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(config, logger)
        self._subscribers: dict[str, dict[str, set[asyncio.Queue[Any]]]] = (
            defaultdict(lambda: defaultdict(set))
        )
        self._shutdown = asyncio.Event()
        self.logger.info("InMemoryMessageBroker initialized.")

    async def publish(self, game_id: str, channel: str, message: Any) -> int:
        """
        Publish a message to a specific game_id and channel.

        Args:
            game_id (str): Identifier to group subscribers.
            channel (str): Channel to deliver the message to.
            message (Any): Message to deliver.

        Returns:
            int: Number of queues successfully notified.
        """
        if self._shutdown.is_set():
            self.logger.warning(
                "Publish ignored: InMemoryMessageBroker is shutting down."
            )
            return 0

        subscribers = self._subscribers.get(game_id, {}).get(channel, set())

        if not subscribers:
            return 0

        tasks = [q.put(message) for q in list(subscribers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                queue_info = list(subscribers)[i]
                self.logger.error(
                    f"InMemoryMessageBroker: Failed to publish to "
                    f"{game_id}:{channel}, queue={queue_info}: {r}",
                    exc_info=r,
                )
            else:
                success_count += 1

        return success_count

    async def subscribe(
        self, game_id: str, channels: BrokerChannels | list[BrokerChannels]
    ) -> AsyncGenerator[Any, None]:
        """
        Subscribe to one or more channels for a given game_id.

        Args:
            game_id (str): Game identifier for namespacing.
            channels (BrokerChannels | list[BrokerChannels]): One or more channels
                                                              to subscribe.

        Returns:
            AsyncGenerator[Any, None]: Yields messages from the subscribed channels.
        """
        if isinstance(channels, str):
            channels_list = [channels]
        elif not channels:

            async def empty_generator() -> AsyncGenerator[Any, None]:
                yield

            return empty_generator()
        else:
            channels_list = channels

        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=100)

        self.logger.info(
            f"InMemoryMessageBroker: Subscribing to channels for game_id={game_id}, "
            f"channels={channels_list}"
        )

        for channel in channels_list:
            self._subscribers[game_id][channel].add(queue)

        async def generator() -> AsyncGenerator[Any, None]:
            try:
                while not self._shutdown.is_set():
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=1.0)
                        if isinstance(message, dict) and message.get("__sentinel__"):
                            break
                        yield message
                    except asyncio.TimeoutError:
                        continue
                    except asyncio.CancelledError:
                        raise
            finally:
                self._unsubscribe(game_id, channels_list, queue)

        return generator()

    def _unsubscribe(
        self, game_id: str, channels: list[BrokerChannels], queue: asyncio.Queue[Any]
    ) -> None:
        """
        Unsubscribe a queue from all specified channels under a game_id.

        Args:
            game_id (str): The game ID the queue was subscribed under.
            channels (list[BrokerChannels]): Channels to remove the queue from.
            queue (asyncio.Queue[Any]): The queue to remove.
        """
        game_data = self._subscribers.get(game_id)
        if not game_data:
            return

        for channel in channels:
            channel_subscribers = game_data.get(channel)
            if channel_subscribers:
                channel_subscribers.discard(queue)
                if not channel_subscribers:
                    del game_data[channel]

        if not game_data:
            self._subscribers.pop(game_id, None)

    async def broadcast(self, channel: str, message: Any) -> int:
        """
        Broadcast a message to all subscribers on a specific channel
        across all game IDs.

        Args:
            channel (str): Channel to broadcast to.
            message (Any): Message to be broadcast.

        Returns:
            int: Number of queues successfully notified.
        """
        if self._shutdown.is_set():
            self.logger.warning(
                "Broadcast ignored: InMemoryMessageBroker is shutting down."
            )
            return 0

        total_notified = 0
        tasks = []

        for game_id in list(self._subscribers.keys()):
            game_channels = self._subscribers.get(game_id)
            if game_channels:
                queues = game_channels.get(channel, set())
                if queues:
                    tasks.extend([q.put(message) for q in list(queues)])
                    total_notified += len(queues)

        if not tasks:
            return 0

        results = await asyncio.gather(*tasks, return_exceptions=True)

        error_count = 0
        for r in results:
            if isinstance(r, Exception):
                self.logger.error(
                    "InMemoryMessageBroker: Broadcast error on"
                    f" channel '{channel}': {r}",
                    exc_info=r,
                )
                error_count += 1

        actual_notified = total_notified - error_count
        self.logger.debug(
            f"InMemoryMessageBroker: Broadcast to '{channel}' reached "
            f"{actual_notified} queues (of {total_notified})."
        )

        return actual_notified

    async def shutdown(self) -> None:
        """
        Gracefully shut down the broker by signaling all queues with a sentinel value
        and clearing all subscription data.
        """
        if self._shutdown.is_set():
            return

        self._shutdown.set()
        self.logger.info("InMemoryMessageBroker: Shutdown initiated.")

        all_queues: set[asyncio.Queue[Any]] = set()
        for game_channels in self._subscribers.values():
            for channel_queues in game_channels.values():
                all_queues.update(channel_queues)

        tasks = [q.put({"__sentinel__": True}) for q in all_queues]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._subscribers.clear()
        self.logger.info("InMemoryMessageBroker: Shutdown completed.")
