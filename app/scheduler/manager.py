from __future__ import annotations

import asyncio
import configparser
from dataclasses import dataclass
import logging
from typing import Any, Optional

from app.broker.message_broker import MessageBroker
from app.scheduler.game_feeder import BaseGameFeeder
from app.scheduler.game_feeder_factory import create_game_feeder
from app.scheduler.scheduler import BaseScheduler, GameScheduler
from db.redis_storage import RedisStorageSingleton as RedisStorage
from utils.load_config import load_config
from utils.logger import get_logger
from utils.get_db_client import get_redis_client

from .game_state_key_builder import GameStateKeyBuilder
from .redis_state_publisher import RedisSchedulerStatePublisher
from .state_publisher import SchedulerStatePublisher


@dataclass(slots=True)
class SchedulerContext:
    game_id: str
    tournament_id: str | None = None
    source: str = "system"


class SchedulerManager:
    """
    Manages the lifecycle of GameScheduler instances.

    Ensures only one scheduler runs per game_id. Handles creation,
    retrieval, and cleanup of schedulers, and supports dynamic
    game feeder resolution.
    """

    _schedulers: dict[str, BaseScheduler]
    _scheduler_tasks: dict[str, asyncio.Task[None]]
    _scheduler_contexts: dict[str, SchedulerContext]
    _broker: MessageBroker
    _lock: asyncio.Lock
    _feeder_factory: dict[str, type[BaseGameFeeder]]

    def __init__(
        self,
        broker: MessageBroker,
        config: configparser.ConfigParser | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Initialize the SchedulerManager.

        Args:
            broker: Instance of the message broker used by schedulers.
            config (ConfigParser): Application configuration containing
                                    storage settings.
            logger (Optional[Logger]): Optional logger instance. If not provided,
                a default logger is retrieved using `get_logger()`.
        """
        self.logger = logger or get_logger()
        self.config = config or load_config()
        self.logger.info("Initializing SchedulerManager...")
        self._broker = broker
        self._schedulers = {}
        self._scheduler_tasks = {}
        self._scheduler_contexts = {}
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._lock = asyncio.Lock()

        self.logger.info("SchedulerManager initialized.")

    def _create_feeder(self, game_id: str) -> BaseGameFeeder:
        """
        Instantiate a game feeder based on the specified type.

        Args:
            game_id: Game identifier.

        Returns:
            BaseGameFeeder: Instance of a concrete feeder class.

        Raises:
            ValueError: If the feeder type is unsupported.
        """
        return create_game_feeder(game_id, self.config, self.logger)

    async def _create_state_publisher(self) -> SchedulerStatePublisher | None:
        if not self.config.getboolean("liveGameRegistry", "enabled", fallback=False):
            return None

        prefix = self.config.get(
            "liveGameRegistry",
            "redisKeyPrefix",
            fallback="live:game",
        )

        ttl = self.config.getint("liveGameRegistry", "ttlSeconds", fallback=30)

        key_builder = GameStateKeyBuilder(prefix)

        return RedisSchedulerStatePublisher(
            storage=RedisStorage(self.config, self.logger),
            key_builder=key_builder,
            ttl_seconds=ttl,
            logger=self.logger,
        )

    def get_scheduler(self, game_id: str) -> BaseScheduler | None:
        """
        Retrieve the active scheduler instance for a specific game.

        Args:
            game_id: Unique identifier for the game.

        Returns:
            BaseScheduler | None: Scheduler instance if found, else None.
        """
        return self._schedulers.get(game_id)

    def has_scheduler(self, game_id: str) -> bool:
        """
        Check if a scheduler exists for the given game ID.

        Args:
            game_id: Unique identifier for the game.

        Returns:
            bool: True if a scheduler exists, False otherwise.
        """
        return game_id in self._schedulers

    async def get_game_data(self, game_id: str) -> dict[str, Any] | None:
        scheduler = self.get_scheduler(game_id)

        if scheduler:
            return await scheduler.get_metadata()
        return None

    async def create_or_get_scheduler(self, context: SchedulerContext) -> tuple[BaseScheduler, asyncio.Task[None]]:
        """
        Create and start a scheduler for the given game if not already running.

        Args:
            context: Scheduler context containing game identifier and tournament information.

        Returns:
            Tuple containing the scheduler instance and its running task.

        Raises:
            ValueError: If the feeder type is unsupported.
            RuntimeError: If scheduler creation fails.
        """
        async with self._lock:
            if context.game_id in self._scheduler_tasks:
                self.logger.info(f"Scheduler already exists for game {context.game_id}. Returning existing.")
                return self._schedulers[context.game_id], self._scheduler_tasks[context.game_id]

            try:
                self.logger.info(f"Creating new scheduler for game {context.game_id}...")

                feeder = self._create_feeder(context.game_id)
                state_publisher = await self._create_state_publisher()

                scheduler = GameScheduler(
                    game_id=context.game_id,
                    broker=self._broker,
                    feeder=feeder,
                    state_publisher=state_publisher,
                )

                task = asyncio.create_task(scheduler.run(), name=f"scheduler_run_{context.game_id}")

                self._schedulers[context.game_id] = scheduler
                self._scheduler_tasks[context.game_id] = task
                self._scheduler_contexts[context.game_id] = context

                task.add_done_callback(self._handle_task_completion)

                self.logger.info(f"Scheduler for game {context.game_id} created and running.")
                return scheduler, task

            except Exception as e:
                self.logger.error(f"Failed to create scheduler for {context.game_id}: {e}", exc_info=True)
                self._schedulers.pop(context.game_id, None)
                self._scheduler_tasks.pop(context.game_id, None)
                self._scheduler_contexts.pop(context.game_id, None)
                raise RuntimeError(f"Scheduler creation failed for {context.game_id}") from e

    # def _handle_task_completion(self, task: asyncio.Task[None]) -> None:
    #     """
    #     Handle completion of a scheduler task, scheduling cleanup.

    #     Args:
    #         task: The completed asyncio Task.
    #     """
    #     try:
    #         task_name = task.get_name()
    #         if not task_name.startswith("scheduler_run_"):
    #             self.logger.error(f"Invalid task name format: {task_name}")
    #             return

    #         game_id = task_name.split("scheduler_run_", 1)[-1]
    #         if task.cancelled():
    #             self.logger.info(f"Scheduler task for {game_id} was cancelled.")
    #         elif task.exception():
    #             self.logger.error(
    #                 f"Scheduler for {game_id} failed: {task.exception()}",
    #                 exc_info=True,
    #             )
    #         else:
    #             self.logger.info(f"Scheduler task for {game_id} completed normally.")

    #         context = self._scheduler_contexts.pop(game_id, None)
    #         if context and context.tournament_id and context.source == "tournament_engine":
    #             self.logger.info(f"Scheduler context for {game_id} removed.")
    #             redis = await get_redis_client(self.config)
    #             await redis.xadd(
    #                 self.config["background"]["StreamKey"],
    #                 {
    #                     "type": "MATCH_FINISHED",
    #                     "match_id": game_id,
    #                     "tournament_id": context.tournament_id,
    #                 },
    #                 maxlen=config.getint("background", "StreamMaxLength", fallback=1000),
    #             )

    #         cleanup = asyncio.create_task(self.cleanup_scheduler(game_id))
    #         self._background_tasks.add(cleanup)
    #         cleanup.add_done_callback(self._background_tasks.discard)

    #     except Exception as e:
    #         self.logger.error(f"Error in _handle_task_completion: {e}", exc_info=True)

    # async def cleanup_scheduler(self, game_id: str) -> None:
    #     """
    #     Cancel and remove the scheduler and task for a specific game.

    #     Args:
    #         game_id: Game identifier to clean up.
    #     """
    #     scheduler = self._schedulers.pop(game_id, None)
    #     task = self._scheduler_tasks.pop(game_id, None)
    #     self._scheduler_contexts.pop(game_id, None)

    #     if scheduler is None and task is None:
    #         self.logger.warning(f"No active scheduler found for cleanup: {game_id}")
    #         return

    #     self.logger.info(f"Cleaning up scheduler for game {game_id}...")

    #     if task and not task.done():
    #         self.logger.info(f"Cancelling task for game {game_id}...")
    #         task.cancel()
    #         try:
    #             await asyncio.wait_for(task, timeout=2.0)
    #             self.logger.info(f"Task for game {game_id} cancelled successfully.")
    #         except asyncio.TimeoutError:
    #             self.logger.warning(f"Timeout while cancelling task for {game_id}.")
    #         except Exception as e:
    #             self.logger.error(f"Error during task cancellation: {e}", exc_info=True)
    #     self.logger.info(f"Scheduler cleanup for game {game_id} complete.")

    def _handle_task_completion(self, task: asyncio.Task[None]) -> None:
        """
        Sync callback executed when a scheduler task completes.

        Since asyncio task callbacks cannot be async, we delegate
        the actual completion processing into a background coroutine.
        """
        background = asyncio.create_task(
            self._process_task_completion(task),
            name=f"process_scheduler_completion_{task.get_name()}",
        )

        self._background_tasks.add(background)
        background.add_done_callback(self._background_tasks.discard)

    async def _process_task_completion(
        self,
        task: asyncio.Task[None],
    ) -> None:
        """
        Process scheduler completion lifecycle.

        Responsibilities:
        - inspect scheduler outcome
        - emit tournament events when applicable
        - cleanup scheduler runtime state
        """
        try:
            task_name = task.get_name()

            if not task_name.startswith("scheduler_run_"):
                self.logger.error(
                    "Invalid task name format: %s",
                    task_name,
                )
                return

            game_id = task_name.split("scheduler_run_", 1)[-1]

            # ------------------------------------------------------------------
            # Task outcome logging
            # ------------------------------------------------------------------

            if task.cancelled():
                self.logger.info(
                    "Scheduler task for game %s was cancelled.",
                    game_id,
                )

            elif task.exception():
                self.logger.error(
                    "Scheduler for game %s failed: %s",
                    game_id,
                    task.exception(),
                    exc_info=True,
                )

            else:
                self.logger.info(
                    "Scheduler task for game %s completed normally.",
                    game_id,
                )

            # ------------------------------------------------------------------
            # Retrieve orchestration context
            # ------------------------------------------------------------------

            context = self._scheduler_contexts.get(game_id)

            # ------------------------------------------------------------------
            # Emit tournament completion event
            # ------------------------------------------------------------------

            # Only emit completion events for tournament-managed games
            if (
                context is not None
                and context.tournament_id is not None
                and not task.cancelled()
                and task.exception() is None
            ):
                try:
                    redis = await get_redis_client(self.config)

                    await redis.xadd(
                        self.config["background"]["StreamKey"],
                        {
                            "type": "MATCH_FINISHED",
                            "match_id": game_id,
                            "tournament_id": context.tournament_id,
                            "source": "scheduler_manager",
                        },
                        maxlen=self.config.getint(
                            "background",
                            "StreamMaxLength",
                            fallback=1000,
                        ),
                    )

                    self.logger.info(
                        "Published MATCH_FINISHED event for game %s in tournament %s.",
                        game_id,
                        context.tournament_id,
                    )

                except Exception:
                    self.logger.exception(
                        "Failed to publish MATCH_FINISHED event for game %s",
                        game_id,
                    )

            # ------------------------------------------------------------------
            # Cleanup runtime resources
            # ------------------------------------------------------------------

            cleanup = asyncio.create_task(
                self.cleanup_scheduler(game_id),
                name=f"cleanup_scheduler_{game_id}",
            )

            self._background_tasks.add(cleanup)
            cleanup.add_done_callback(self._background_tasks.discard)

        except Exception:
            self.logger.exception("Error while processing scheduler task completion.")

    async def cleanup_scheduler(self, game_id: str) -> None:
        """
        Cleanup scheduler runtime state for a game.

        Responsibilities:
        - remove scheduler registries
        - cancel dangling tasks if needed
        - release memory/resources
        """
        scheduler = self._schedulers.pop(game_id, None)
        task = self._scheduler_tasks.pop(game_id, None)
        self._scheduler_contexts.pop(game_id, None)

        if scheduler is None and task is None:
            self.logger.warning(
                "No active scheduler found for cleanup: %s",
                game_id,
            )
            return

        self.logger.info(
            "Cleaning up scheduler for game %s...",
            game_id,
        )

        # ------------------------------------------------------------------
        # Cancel unfinished task
        # ------------------------------------------------------------------

        if task and not task.done():
            self.logger.info(
                "Cancelling running task for game %s...",
                game_id,
            )

            task.cancel()

            try:
                await asyncio.wait_for(task, timeout=2.0)

                self.logger.info(
                    "Task for game %s cancelled successfully.",
                    game_id,
                )

            except asyncio.TimeoutError:
                self.logger.warning(
                    "Timeout while cancelling task for game %s.",
                    game_id,
                )

            except Exception:
                self.logger.exception(
                    "Error during task cancellation for game %s.",
                    game_id,
                )

        self.logger.info(
            "Scheduler cleanup for game %s complete.",
            game_id,
        )

    async def shutdown(self) -> None:
        """
        Gracefully shut down all running schedulers and tasks.

        Should be called during service shutdown to clean up resources.
        """
        self.logger.info("Shutting down all schedulers...")
        async with self._lock:
            game_ids = list(self._schedulers.keys())

            if not game_ids:
                self.logger.info("No schedulers to shut down.")
                return

            self.logger.info(f"Cleaning up schedulers for games: {game_ids}")

            cleanup_tasks = [
                asyncio.create_task(
                    self.cleanup_scheduler(game_id),
                    name=f"shutdown_cleanup_{game_id}",
                )
                for game_id in game_ids
            ]

            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            if self._schedulers or self._scheduler_tasks:
                self.logger.warning(f"Remaining schedulers: {list(self._schedulers.keys())}")
                self.logger.warning(f"Remaining tasks: {list(self._scheduler_tasks.keys())}")
            else:
                self.logger.info("All schedulers shut down cleanly.")

        self.logger.info("SchedulerManager shutdown complete.")
