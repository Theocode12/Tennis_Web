from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from app.shared.enums.broker_channels import BrokerChannels

if TYPE_CHECKING:
    from app.core.context import AppContext

MessageProcessor = Callable[
    [dict[str, Any]], Awaitable[tuple[str, dict[str, Any]] | None]
]


class BrokerRelay:
    def __init__(self, context: AppContext):
        self._context = context
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    def _create_subscription_key(
        self, game_id: str, channels: list[BrokerChannels]
    ) -> str:
        return f"{game_id}:{'+'.join(sorted(c.value for c in channels))}"

    async def start_listener(
        self,
        game_id: str,
        channels: list[BrokerChannels],
        namespace: str,
        processor: MessageProcessor,
    ) -> None:
        key = self._create_subscription_key(game_id, channels)
        async with self._lock:
            if key in self._tasks:
                self._context.logger.debug(
                    f"Reusing existing broker relay for {key}."
                )
                return

            task = asyncio.create_task(
                self._listener(game_id, channels, namespace, processor),
                name=f"broker_relay_{key}",
            )
            self._tasks[key] = task

            def _done_callback(t: asyncio.Task[None]) -> None:
                self._tasks.pop(key, None)
                self._context.logger.debug(f"Broker relay task removed: {key}")

            task.add_done_callback(_done_callback)
            self._context.logger.info(f"Broker relay started for {key}.")

    async def _listener(
        self,
        game_id: str,
        channels: list[BrokerChannels],
        namespace: str,
        processor: MessageProcessor,
    ) -> None:
        try:
            iterator = await self._context.broker.subscribe(game_id, channels)
            async for message in iterator:
                if not isinstance(message, dict):
                    continue

                result = await processor(message)
                if not result:
                    continue

                event_name, payload = result
                await self._context.sio.emit(
                    event_name, payload, room=game_id, namespace=namespace
                )
        except asyncio.CancelledError:
            self._context.logger.debug(f"Broker relay cancelled for {game_id}.")
            raise
        except Exception as e:
            self._context.logger.error(
                f"Error in broker relay ({game_id}, {channels}): {e}", exc_info=True
            )
        finally:
            self._context.logger.info(
                f"Broker relay for game_id={game_id}, channels={channels} ended."
            )

    async def stop_all(self) -> None:
        async with self._lock:
            tasks_to_cancel = list(self._tasks.values())
            self._tasks.clear()

        if not tasks_to_cancel:
            return

        for task in tasks_to_cancel:
            task.cancel()
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        self._context.logger.info("All broker relays have been stopped.")
