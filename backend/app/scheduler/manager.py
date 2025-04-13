import asyncio
import logging
from typing import Dict, Optional, Tuple, Type

from .scheduler import GameScheduler, BaseScheduler
from .game_feeder import BaseGameFeeder, RedisGameFeeder, FileGameFeeder
from backend.app.broker.message_broker import MessageBroker
from backend.app.shared.lib.singleton_metaclass import SingletonMeta

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchedulerManager(metaclass=SingletonMeta):
    """
    Manages the lifecycle of GameScheduler instances.

    Ensures that only one scheduler runs per game_id and handles
    creation, retrieval, and cleanup.
    """
    _schedulers: Dict[str, BaseScheduler]
    _scheduler_tasks: Dict[str, asyncio.Task]
    _broker: MessageBroker
    _lock: asyncio.Lock
    _feeder_factory: Dict[str, Type[BaseGameFeeder]] # Factory pattern for feeders

    def __init__(self, broker: MessageBroker) -> None:
        """
        Initializes the SchedulerManager.

        Args:
            broker: The message broker instance to be used by schedulers.
        """
        if hasattr(self, '_lock'): # Avoid re-initialization in Singleton
             return
        logger.info("Initializing SchedulerManager...")
        self._schedulers = {}
        self._scheduler_tasks = {}
        self._broker = broker
        self._lock = asyncio.Lock()
        # Register available feeder types
        self._feeder_factory = {
            "redis": RedisGameFeeder,
            "file": FileGameFeeder,
        }
        logger.info("SchedulerManager initialized.")

    def _get_feeder_type(self, game_id: str) -> str:
        """
        Determines the appropriate feeder type for a game.
        Placeholder logic: Default to 'redis', could be extended
        to check config or database.
        """
        # Example: Could check a config file or database setting for the game_id
        # config = load_game_config(game_id)
        # return config.get('feeder_type', 'redis')
        logger.debug(f"Determining feeder type for game {game_id}. Defaulting to 'file'.")
        return "file" # Default to Redis for now

    def _create_feeder(self, game_id: str, feeder_type_name: str) -> BaseGameFeeder:
        """Creates a feeder instance based on the type name."""
        feeder_class = self._feeder_factory.get(feeder_type_name)
        if not feeder_class:
            raise ValueError(f"Unsupported feeder type: {feeder_type_name}")
        logger.info(f"Creating '{feeder_type_name}' feeder for game {game_id}")
        return feeder_class(game_id=game_id)

    def get_scheduler(self, game_id: str) -> Optional[BaseScheduler]:
        """
        Retrieves an active scheduler instance for a given game_id.

        Args:
            game_id: The unique identifier for the game.

        Returns:
            The scheduler instance if active, otherwise None.
        """
        return self._schedulers.get(game_id)

    async def create_or_get_scheduler(self, game_id: str) -> Tuple[BaseScheduler, asyncio.Task]:
        """
        Creates a new scheduler and starts it if one doesn't exist for the game_id,
        otherwise returns the existing active scheduler and its task.

        Args:
            game_id: The unique identifier for the game.

        Returns:
            A tuple containing the scheduler instance and its running task.

        Raises:
            ValueError: If an unsupported feeder type is determined.
            RuntimeError: If scheduler creation fails unexpectedly.
        """
        async with self._lock:
            # Check if already exists
            if game_id in self._scheduler_tasks:
                logger.info(f"Scheduler for game {game_id} already exists. Returning existing instance.")
                task = self._scheduler_tasks[game_id]
                scheduler = self._schedulers[game_id]
                return scheduler, task

            logger.info(f"Creating new scheduler for game {game_id}...")
            try:
                # 1. Determine and create the appropriate feeder
                feeder_type_name = self._get_feeder_type(game_id)
                feeder = self._create_feeder(game_id, feeder_type_name)

                # 2. Create the scheduler instance
                scheduler = GameScheduler(game_id=game_id, broker=self._broker, feeder=feeder)
                self._schedulers[game_id] = scheduler

                # 3. Create and run the scheduler task
                task_name = f"scheduler_run_{game_id}"
                scheduler_task = asyncio.create_task(scheduler.run(), name=task_name)
                self._scheduler_tasks[game_id] = scheduler_task

                # 4. Add callback for automatic cleanup when task finishes
                scheduler_task.add_done_callback(self._handle_task_completion)

                logger.info(f"Scheduler task for game {game_id} created and started.")
                
                return scheduler, scheduler_task

            except Exception as e:
                logger.error(f"Failed to create scheduler for game {game_id}: {e}", exc_info=True)
                # Clean up any partial state if creation failed mid-way
                self._schedulers.pop(game_id, None)
                self._scheduler_tasks.pop(game_id, None)
                raise RuntimeError(f"Scheduler creation failed for {game_id}") from e

    def _handle_task_completion(self, task: asyncio.Task) -> None:
        """
        Callback executed when a scheduler task finishes (normally or with error).
        Schedules the actual cleanup to run asynchronously.
        """
        task_name = task.get_name()
        try:
            if task_name.startswith("scheduler_run_"):
                game_id = task_name.split("scheduler_run_", 1)[1]
            else:
                logger.error(f"Could not determine game_id from completed task name: {task_name}")
                return

            exception = task.exception()
            if exception:
                logger.error(f"Scheduler task for game {game_id} finished with error: {exception}", exc_info=exception)
            else:
                logger.info(f"Scheduler task for game {game_id} finished normally.")

            asyncio.create_task(self.cleanup_scheduler(game_id), name=f"cleanup_scheduler_{game_id}")

        # it is okay for task.exception() to raise an exception
        # because we are already in the context of a task that is done
        except asyncio.CancelledError:
            pass
        except Exception as e:
            # Catch errors within the callback itself
            logger.error(f"Error in _handle_task_completion for task {task_name}: {e}", exc_info=True)


    async def cleanup_scheduler(self, game_id: str) -> bool:
        """
        Stops and removes a specific scheduler and its task.
        This is safe to call even if the scheduler task has already finished.

        Args:
            game_id: The unique identifier for the game scheduler to clean up.

        Returns:
            True if a scheduler was found and cleanup was attempted, False otherwise.
        """
        scheduler = self._schedulers.pop(game_id, None)
        task = self._scheduler_tasks.pop(game_id, None)

        if scheduler is None and task is None:
            logger.warning(f"Cleanup requested for game {game_id}, but no active scheduler or task found.")
            return False

        logger.info(f"Cleaning up scheduler for game {game_id}...")
        if task and not task.done():
            logger.info(f"Cancelling running scheduler task for game {game_id}...")
            task.cancel()
            try:
                # Give cancellation a chance to propagate and run finally blocks
                # Use a small timeout to avoid waiting indefinitely if cancellation hangs
                await asyncio.wait_for(task, timeout=2.0)
            except asyncio.CancelledError:
                print(f"Scheduler task for game {game_id} cancelled successfully.")
                logger.info(f"Scheduler task for game {game_id} cancelled successfully.")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for scheduler task {game_id} cancellation.")
            except Exception as e:
                # Log unexpected errors during task waiting/cancellation
                logger.error(f"Error awaiting cancelled task for {game_id}: {e}", exc_info=True)

        logger.info(f"Scheduler cleanup for game {game_id} complete.")
        return True

    async def shutdown(self) -> None:
        """
        Gracefully shuts down all active schedulers.
        Should be called during application shutdown.
        """
        logger.info("SchedulerManager shutting down all schedulers...")
        async with self._lock:
            # Create a list of game_ids to avoid modifying dict while iterating
            game_ids = list(self._schedulers.keys())
            if not game_ids:
                logger.info("No active schedulers to shut down.")
                return

            logger.info(f"Found active schedulers for games: {game_ids}")
            # Initiate cleanup for all active schedulers concurrently
            cleanup_tasks = [
                asyncio.create_task(self.cleanup_scheduler(gid), name=f"shutdown_cleanup_{gid}")
                for gid in game_ids
            ]

            # Wait for all cleanup tasks to complete
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            # Verify dictionaries are empty (they should be after cleanup)
            remaining_schedulers = list(self._schedulers.keys())
            remaining_tasks = list(self._scheduler_tasks.keys())
            if remaining_schedulers or remaining_tasks:
                 logger.warning(f"Schedulers remaining after shutdown: {remaining_schedulers}")
                 logger.warning(f"Tasks remaining after shutdown: {remaining_tasks}")
            else:
                 logger.info("All schedulers cleaned up successfully.")

        logger.info("SchedulerManager shutdown complete.")
