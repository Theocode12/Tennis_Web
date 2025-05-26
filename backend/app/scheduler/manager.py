from __future__ import annotations

import asyncio
import configparser
import logging

from utils.load_config import load_config
from utils.logger import get_logger

from app.broker.message_broker import MessageBroker
from app.scheduler.game_feeder import BaseGameFeeder
from app.scheduler.game_feeder_factory import create_game_feeder
from app.scheduler.scheduler import BaseScheduler, GameScheduler
from app.shared.lib.singleton_metaclass import SingletonMeta


class SchedulerManager(metaclass=SingletonMeta):
    """
    Manages the lifecycle of GameScheduler instances.

    Ensures only one scheduler runs per game_id. Handles creation,
    retrieval, and cleanup of schedulers, and supports dynamic
    game feeder resolution.
    """

    _schedulers: dict[str, BaseScheduler]
    _scheduler_tasks: dict[str, asyncio.Task[None]]
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

    def get_scheduler(self, game_id: str) -> BaseScheduler | None:
        """
        Retrieve the active scheduler instance for a specific game.

        Args:
            game_id: Unique identifier for the game.

        Returns:
            BaseScheduler | None: Scheduler instance if found, else None.
        """
        return self._schedulers.get(game_id)

    async def create_or_get_scheduler(
        self, game_id: str
    ) -> tuple[BaseScheduler, asyncio.Task[None]]:
        """
        Create and start a scheduler for the given game if not already running.

        Args:
            game_id: Game identifier.

        Returns:
            Tuple containing the scheduler instance and its running task.

        Raises:
            ValueError: If the feeder type is unsupported.
            RuntimeError: If scheduler creation fails.
        """
        async with self._lock:
            if game_id in self._scheduler_tasks:
                self.logger.info(
                    f"Scheduler already exists for game {game_id}. "
                    "Returning existing."
                )
                return self._schedulers[game_id], self._scheduler_tasks[game_id]

            try:
                self.logger.info(f"Creating new scheduler for game {game_id}...")

                feeder = self._create_feeder(game_id)

                scheduler = GameScheduler(
                    game_id=game_id, broker=self._broker, feeder=feeder
                )
                task = asyncio.create_task(
                    scheduler.run(), name=f"scheduler_run_{game_id}"
                )

                self._schedulers[game_id] = scheduler
                self._scheduler_tasks[game_id] = task

                task.add_done_callback(self._handle_task_completion)

                self.logger.info(
                    f"Scheduler for game {game_id} created and running."
                )
                return scheduler, task

            except Exception as e:
                self.logger.error(
                    f"Failed to create scheduler for {game_id}: {e}", exc_info=True
                )
                self._schedulers.pop(game_id, None)
                self._scheduler_tasks.pop(game_id, None)
                raise RuntimeError(f"Scheduler creation failed for {game_id}") from e

    def _handle_task_completion(self, task: asyncio.Task[None]) -> None:
        """
        Handle completion of a scheduler task, scheduling cleanup.

        Args:
            task: The completed asyncio Task.
        """
        try:
            task_name = task.get_name()
            if not task_name.startswith("scheduler_run_"):
                self.logger.error(f"Invalid task name format: {task_name}")
                return

            game_id = task_name.split("scheduler_run_", 1)[-1]
            if task.cancelled():
                self.logger.info(f"Scheduler task for {game_id} was cancelled.")
            elif task.exception():
                self.logger.error(
                    f"Scheduler for {game_id} failed: {task.exception()}",
                    exc_info=True,
                )
            else:
                self.logger.info(f"Scheduler task for {game_id} completed normally.")

            cleanup = asyncio.create_task(self.cleanup_scheduler(game_id))
            self._background_tasks.add(cleanup)
            cleanup.add_done_callback(self._background_tasks.discard)

        except Exception as e:
            self.logger.error(
                f"Error in _handle_task_completion: {e}", exc_info=True
            )

    async def cleanup_scheduler(self, game_id: str) -> None:
        """
        Cancel and remove the scheduler and task for a specific game.

        Args:
            game_id: Game identifier to clean up.
        """
        scheduler = self._schedulers.pop(game_id, None)
        task = self._scheduler_tasks.pop(game_id, None)

        if scheduler is None and task is None:
            self.logger.warning(f"No active scheduler found for cleanup: {game_id}")
            return

        self.logger.info(f"Cleaning up scheduler for game {game_id}...")

        if task and not task.done():
            self.logger.info(f"Cancelling task for game {game_id}...")
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=2.0)
                self.logger.info(f"Task for game {game_id} cancelled successfully.")
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout while cancelling task for {game_id}.")
            except Exception as e:
                self.logger.error(
                    f"Error during task cancellation: {e}", exc_info=True
                )

        self.logger.info(f"Scheduler cleanup for game {game_id} complete.")

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
                self.logger.warning(
                    f"Remaining schedulers: {list(self._schedulers.keys())}"
                )
                self.logger.warning(
                    f"Remaining tasks: {list(self._scheduler_tasks.keys())}"
                )
            else:
                self.logger.info("All schedulers shut down cleanly.")

        self.logger.info("SchedulerManager shutdown complete.")
