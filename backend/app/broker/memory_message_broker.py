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
        if isinstance(channels, BrokerChannels):
            channels_list = [channels]
        elif len(channels) == 0:

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
                        self.logger.debug(
                            f"InMemoryMessageBroker: Received message {message}."
                        )
                        yield message
                    except asyncio.TimeoutError:
                        continue
                    except asyncio.CancelledError as e:
                        raise e
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
        self.logger.debug(
            f"Unsubscribing queue from channels :{channels}. Game id {game_id}."
        )
        channel_map = self._subscribers.get(game_id)
        if not channel_map:
            return

        for channel in channels:
            subscriber_queues = channel_map.get(channel)
            if subscriber_queues:
                subscriber_queues.discard(queue)
                if not subscriber_queues:
                    del channel_map[channel]

        if not channel_map:
            self._subscribers.pop(game_id, None)
        self.logger.debug(
            f"Unsubscribe by listener completed for game_id {game_id}."
        )

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

        # Actively unblock consumers
        tasks = [q.put({"__sentinel__": True}) for q in all_queues]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._subscribers.clear()
        self.logger.info("InMemoryMessageBroker: Shutdown completed.")
