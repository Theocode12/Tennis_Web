from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from db.file_storage import FileStorage  # Assuming this is the correct path

from app.broker.memory_message_broker import (
    InMemoryMessageBroker,  # Use in-memory for testing
)
from app.scheduler.game_feeder import BaseGameFeeder, FileGameFeeder

# --- Adjust imports based on actual project structure ---
# Core components under test and dependencies
from app.scheduler.manager import SchedulerManager
from app.scheduler.scheduler import GameScheduler
from app.shared.lib.singleton_metaclass import SingletonMeta

# --- Test Configuration ---

# Disable unnecessary logging from the application during tests to keep output clean
logging.getLogger("app.websockets.scheduler.manager").setLevel(logging.WARNING)
logging.getLogger("app.websockets.scheduler.scheduler").setLevel(logging.WARNING)
logging.getLogger("app.websockets.scheduler.game_feeder").setLevel(logging.WARNING)
# logging.basicConfig(level=logging.DEBUG) # Uncomment for detailed debugging

# --- Test Suite ---


class TestSchedulerManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up for each test."""

        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir_path = self.temp_dir_obj.name
        self.test_file_storage = BackendFileStorage(self.temp_dir_path)

        self.broker = InMemoryMessageBroker()
        self.manager = SchedulerManager(broker=self.broker)
        self.created_tasks_map: dict[str, asyncio.Task] = {}

    async def asyncTearDown(self):
        """Clean up after each test."""
        # 1. Ensure manager shutdown is called to clean up internal tasks/schedulers
        # Check if the instance still exists (it might have been cleaned up by tests)
        manager_instance = SingletonMeta._instances.get(SchedulerManager)
        if manager_instance:
            await manager_instance.shutdown()
            # Short sleep to allow background cleanup tasks scheduled by shutdown/callbacks to run
            await asyncio.sleep(0.05)

        # 2. Clean up the broker's resources
        await self.broker.shutdown()
        await asyncio.sleep(0.01)  # Allow broker cleanup tasks

        # 3. Clean up temporary directory
        self.temp_dir_obj.cleanup()

        # 4. Ensure Singleton is clean after each test
        SingletonMeta._instances.pop(SchedulerManager, None)

        # 5. Allow event loop to process final cleanup tasks
        await asyncio.sleep(0.01)

    # --- Helper Methods ---

    def _create_game_file(self, game_id: str, scores: list[dict]) -> Path:
        """Helper to create a game data file in the temp storage."""
        file_path = self.test_file_storage.get_game_path(game_id)
        game_data = {"scores": scores}
        with open(file_path, "w") as f:
            json.dump(game_data, f)
        return file_path

    def _patch_create_feeder(self):
        """
        Returns a patch context manager for the manager's _create_feeder.
        Injects the correct test storage instance when creating FileGameFeeder.
        This is NECESSARY because the default _create_feeder in the manager
        likely doesn't know about the test storage instance.
        """
        # Use 'self' from the outer scope (the test instance) to access test_file_storage
        test_instance_self = self

        # Define the replacement function for _create_feeder
        def patched_create_feeder(
            game_id: str, feeder_type_name: str
        ) -> BaseGameFeeder:
            if feeder_type_name == "file":
                # logging.debug(f"Patched _create_feeder: Creating FileGameFeeder for {game_id}")
                # Access test_file_storage from the test instance captured in the closure
                return FileGameFeeder(
                    game_id=game_id, storage=test_instance_self.test_file_storage
                )
            elif feeder_type_name == "redis":
                # This path would require similar injection for Redis storage if tested
                # For now, raise an error if redis is unexpectedly requested in tests using this patch
                raise NotImplementedError(
                    "Redis feeder path not configured in this specific patch"
                )
            else:
                # Fallback for potentially unknown types if manager logic changes
                raise ValueError(
                    f"Unsupported feeder type in patched creator: {feeder_type_name}"
                )

        # Return the patch object so it can be used in a 'with' statement
        # autospec=True helps ensure the mock has the same signature as the original
        return patch.object(
            self.manager,
            "_create_feeder",
            side_effect=patched_create_feeder,
            autospec=True,
        )

    # --- Test Cases ---

    def test_singleton_behavior(self):
        """Verify that SchedulerManager follows the Singleton pattern."""
        manager1 = SchedulerManager(broker=self.broker)
        manager2 = SchedulerManager(broker=self.broker)
        self.assertIs(
            manager1,
            self.manager,
            "Manager obtained later should be the same as in setUp",
        )
        self.assertIs(
            manager1, manager2, "Multiple calls should return the same instance"
        )

        # Test with a different broker instance (should still return the first instance)
        broker2 = InMemoryMessageBroker()
        manager3 = SchedulerManager(broker=broker2)
        self.assertIs(
            manager1,
            manager3,
            "Call with different args should return first instance",
        )
        self.assertIs(
            manager1._broker,
            self.broker,
            "Singleton should retain the initially provided broker",
        )

    async def test_create_new_scheduler_success_file(self):
        """Test creating a scheduler successfully using FileFeeder."""
        game_id = "game_file_create_success"

        # --- Patching Strategy ---
        # 1. Patch _get_feeder_type to force 'file'
        # 2. Patch _create_feeder (using helper) to inject test storage
        with (
            patch.object(self.manager, "_get_feeder_type", return_value="file"),
            self._patch_create_feeder(),
        ):  # Apply the feeder creation patch
            scheduler, task = await self.manager.create_or_get_scheduler(game_id)
            self.created_tasks_map[game_id] = task  # Store for potential checks

        self.assertIsNotNone(scheduler, "Scheduler should be created")
        self.assertIsNotNone(task, "Task should be created")
        self.assertIn(
            game_id,
            self.manager._schedulers,
            "Scheduler should be stored in manager's dict",
        )
        self.assertIn(
            game_id,
            self.manager._scheduler_tasks,
            "Task should be stored in manager's dict",
        )
        self.assertIs(
            self.manager._schedulers[game_id],
            scheduler,
            "Stored scheduler should match returned one",
        )
        self.assertIs(
            self.manager._scheduler_tasks[game_id],
            task,
            "Stored task should match returned one",
        )
        self.assertIsInstance(
            scheduler, GameScheduler, "Scheduler should be a GameScheduler instance"
        )
        self.assertIsInstance(
            scheduler.feeder,
            FileGameFeeder,
            "Scheduler's feeder should be FileGameFeeder",
        )
        self.assertEqual(
            scheduler.game_id, game_id, "Scheduler should have the correct game_id"
        )
        self.assertFalse(task.done(), "Task should be running or scheduled to run")

        # Allow task to potentially start processing (yield control)
        await asyncio.sleep(0.01)

        # Trigger subscription to controls channel task to end
        await self.broker.publish(game_id, "controls", None)

    async def test_get_existing_scheduler(self):
        """Test getting a scheduler that already exists returns the same instance."""
        game_id = "game_file_exists_1"
        scores = [{"point": 1}]
        self._create_game_file(game_id, scores)

        # Patch feeder selection and creation logic for the first call
        with (
            patch.object(self.manager, "_get_feeder_type", return_value="file"),
            self._patch_create_feeder(),
        ):
            scheduler1, task1 = await self.manager.create_or_get_scheduler(game_id)
            self.created_tasks_map[game_id] = task1

            # Mock the methods that *should not* be called on the second attempt
            with (
                patch.object(
                    self.manager,
                    "_get_feeder_type",
                    wraps=self.manager._get_feeder_type,
                ) as mock_get_type,
                patch.object(
                    self.manager, "_create_feeder", wraps=self.manager._create_feeder
                ) as mock_create_feeder,
                patch(
                    "app.scheduler.manager.GameScheduler", wraps=GameScheduler
                ) as mock_game_scheduler_init,
            ):  # Patch constructor
                # Try creating/getting again - should return existing without calling creation logic
                scheduler2, task2 = await self.manager.create_or_get_scheduler(
                    game_id
                )

                # Assert that creation logic was NOT called again
                mock_get_type.assert_not_called()
                mock_create_feeder.assert_not_called()
                mock_game_scheduler_init.assert_not_called()

        # Assert that the returned instances are the same
        self.assertIs(
            scheduler1,
            scheduler2,
            "Second call should return the same scheduler instance",
        )
        self.assertIs(
            task1, task2, "Second call should return the same task instance"
        )
        # Assert that the manager only stores one instance
        self.assertEqual(
            len(self.manager._schedulers), 1, "Only one scheduler should be stored"
        )
        self.assertEqual(
            len(self.manager._scheduler_tasks), 1, "Only one task should be stored"
        )

    async def test_create_scheduler_unsupported_feeder_type(self):
        """Test error handling when _get_feeder_type returns an unsupported type."""
        game_id = "game_bad_feeder_type"

        # Patch only the type selection to return an invalid type
        with patch.object(
            self.manager, "_get_feeder_type", return_value="invalid_type_name"
        ):
            # Expect RuntimeError because _create_feeder will raise ValueError, caught by create_or_get_scheduler
            with self.assertRaises(RuntimeError):
                await self.manager.create_or_get_scheduler(game_id)

        # Assert that no scheduler or task was stored due to the failure
        self.assertNotIn(
            game_id,
            self.manager._schedulers,
            "Scheduler should not be stored on failure",
        )
        self.assertNotIn(
            game_id,
            self.manager._scheduler_tasks,
            "Task should not be stored on failure",
        )

    async def test_create_scheduler_feeder_init_error(self):
        """Test error handling if the feeder's __init__ (via _create_feeder) fails."""
        game_id = "game_feeder_init_fail"
        # No game file needed, we'll make the feeder creation fail directly

        # Patch _create_feeder to raise an error during instantiation attempt
        def failing_create_feeder(
            game_id: str, feeder_type_name: str
        ) -> BaseGameFeeder:
            if feeder_type_name == "file":
                raise ValueError(
                    "Simulated feeder init failure"
                )  # Simulate error in FileFeeder.__init__
            raise NotImplementedError  # Should not happen if _get_feeder_type is patched correctly

        with (
            patch.object(self.manager, "_get_feeder_type", return_value="file"),
            patch.object(
                self.manager, "_create_feeder", side_effect=failing_create_feeder
            ),
        ):
            # Expect RuntimeError from create_or_get_scheduler's exception handling
            with self.assertRaisesRegex(
                RuntimeError, f"Scheduler creation failed for {game_id}"
            ):
                await self.manager.create_or_get_scheduler(game_id)

        # Assert that no scheduler or task was stored
        self.assertNotIn(game_id, self.manager._schedulers)
        self.assertNotIn(game_id, self.manager._scheduler_tasks)

    async def test_create_scheduler_task_run_error_triggers_cleanup(self):
        """Test handling when the scheduler task fails during run (e.g., file not found) and verify auto-cleanup."""
        game_id = "game_run_fail_no_file"
        # Do NOT create the game file for this game_id

        # Patch feeder selection and creation logic
        with (
            patch.object(self.manager, "_get_feeder_type", return_value="file"),
            self._patch_create_feeder(),
        ):
            scheduler, task = await self.manager.create_or_get_scheduler(game_id)
            self.created_tasks_map[game_id] = task

        # The error (FileNotFoundError) happens inside the task when FileGameFeeder._load_batch is called.
        # We need to await the task and expect it to raise the exception.
        with self.assertRaises(FileNotFoundError):
            # Wait for the task to complete (and raise its internal exception)
            await scheduler.start()
            await asyncio.wait_for(task, timeout=1.0)

        # --- Verify Automatic Cleanup via Callback ---
        # Check if the manager cleaned up automatically via the _handle_task_completion callback
        # Allow time for the callback and the cleanup task it schedules to run
        await asyncio.sleep(0.1)  # Adjust sleep if needed

        self.assertNotIn(
            game_id,
            self.manager._schedulers,
            "Scheduler should be cleaned up automatically after task error",
        )
        self.assertNotIn(
            game_id,
            self.manager._scheduler_tasks,
            "Task should be cleaned up automatically after task error",
        )
        self.assertTrue(task.done(), "Task should be marked as done")
        self.assertIsNotNone(
            task.exception(), "Task should have recorded the exception"
        )
        self.assertIsInstance(task.exception(), FileNotFoundError)

    async def test_get_scheduler_exists(self):
        """Test get_scheduler retrieves an existing, active scheduler."""
        game_id = "game_get_exists"
        self._create_game_file(game_id, [{"p": 1}])  # Create file with some data
        with (
            patch.object(self.manager, "_get_feeder_type", return_value="file"),
            self._patch_create_feeder(),
        ):
            scheduler1, task1 = await self.manager.create_or_get_scheduler(game_id)
            self.created_tasks_map[game_id] = task1

        # Use the manager's public method to retrieve
        retrieved_scheduler = self.manager.get_scheduler(game_id)
        self.assertIs(
            retrieved_scheduler,
            scheduler1,
            "get_scheduler should return the correct active instance",
        )

    async def test_get_scheduler_not_exists(self):
        """Test get_scheduler returns None for a game_id that was never created."""
        retrieved_scheduler = self.manager.get_scheduler("game_get_nonexistent")
        self.assertIsNone(
            retrieved_scheduler,
            "get_scheduler should return None for unknown game_id",
        )

    async def test_cleanup_active_scheduler(self):
        """Test manually cleaning up a scheduler whose task is still running."""
        game_id = "game_cleanup_active"
        # Use a file with enough data or make scheduler wait to ensure it's active
        scores = [{"point": i} for i in range(5)]  # Some data points
        self._create_game_file(game_id, scores)

        with (
            patch.object(self.manager, "_get_feeder_type", return_value="file"),
            self._patch_create_feeder(),
        ):
            scheduler, task = await self.manager.create_or_get_scheduler(game_id)
            self.created_tasks_map[game_id] = task

        # Verify initial state
        self.assertIn(game_id, self.manager._schedulers)
        self.assertIn(game_id, self.manager._scheduler_tasks)
        await asyncio.sleep(0.01)  # Ensure task has a chance to start
        self.assertFalse(task.done(), "Task should be active before cleanup")

        # Perform manual cleanup
        result = await self.manager.cleanup_scheduler(game_id)
        await asyncio.sleep(0.01)  # Allow cancellation propagation

        # Assert cleanup results
        self.assertTrue(
            result, "cleanup_scheduler should return True for an existing scheduler"
        )
        self.assertNotIn(
            game_id,
            self.manager._schedulers,
            "Scheduler should be removed from manager after cleanup",
        )
        self.assertNotIn(
            game_id,
            self.manager._scheduler_tasks,
            "Task should be removed from manager after cleanup",
        )
        self.assertTrue(
            task.cancelled(), "Task should be cancelled by manual cleanup"
        )

    async def test_cleanup_finished_scheduler(self):
        """Test manually cleaning up a scheduler whose task has already completed normally."""
        game_id = "game_cleanup_finished"
        # Use an empty file so the task finishes almost immediately
        self._create_game_file(game_id, [])

        with (
            patch.object(self.manager, "_get_feeder_type", return_value="file"),
            self._patch_create_feeder(),
        ):
            scheduler, task = await self.manager.create_or_get_scheduler(game_id)
            self.created_tasks_map[game_id] = task

        # Wait for the task to finish naturally
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            self.fail("Task did not finish in time")

        # Verify task state before manual cleanup
        self.assertTrue(
            task.done(), "Task should be done before manual cleanup call"
        )
        self.assertFalse(
            task.cancelled(), "Task should not be cancelled if finished normally"
        )
        self.assertIsNone(
            task.exception(), "Task should have no exception if finished normally"
        )

        # --- Test manual cleanup on an already finished task ---
        # The completion callback might or might not have run yet.
        # Call cleanup manually to test its handling of already-done tasks.
        if (
            game_id in self.manager._schedulers
        ):  # Check if callback already cleaned up
            result = await self.manager.cleanup_scheduler(game_id)
            # It should still return True as it found the entries initially
            self.assertTrue(
                result,
                "cleanup_scheduler should return True even if task was already done",
            )
        else:
            # If callback already ran, cleanup would return False, but state should be clean
            self.assertNotIn(game_id, self.manager._scheduler_tasks)
            # We can't assert result is False here as it depends on timing.

        # Assert final state after potential callback OR manual cleanup
        self.assertNotIn(
            game_id, self.manager._schedulers, "Scheduler should be removed"
        )
        self.assertNotIn(
            game_id, self.manager._scheduler_tasks, "Task should be removed"
        )
        self.assertTrue(task.done())  # State remains done
        self.assertFalse(task.cancelled())  # State remains not cancelled

    async def test_cleanup_non_existent_scheduler(self):
        """Test cleaning up a scheduler that doesn't exist in the manager."""
        game_id = "game_cleanup_non_existent"
        result = await self.manager.cleanup_scheduler(game_id)
        self.assertFalse(
            result, "cleanup_scheduler should return False for non-existent game_id"
        )
        # Verify manager state remains empty for this ID
        self.assertNotIn(game_id, self.manager._schedulers)
        self.assertNotIn(game_id, self.manager._scheduler_tasks)

    async def test_task_completion_callback_normal_cleanup(self):
        """Verify the done callback cleans up resources on normal task completion."""
        game_id = "game_callback_normal_cleanup"
        # Empty file for quick completion
        self._create_game_file(game_id, [])

        with (
            patch.object(self.manager, "_get_feeder_type", return_value="file"),
            self._patch_create_feeder(),
        ):
            scheduler, task = await self.manager.create_or_get_scheduler(game_id)
            self.created_tasks_map[game_id] = task

        # Wait for the task to finish
        await asyncio.wait_for(task, timeout=1.0)

        # --- Verify Automatic Cleanup ---
        # Wait a bit longer for the callback and the cleanup task it schedules to run
        await asyncio.sleep(
            0.1
        )  # Needs enough time for create_task(cleanup_scheduler) to run

        self.assertTrue(task.done(), "Task should be done")
        self.assertFalse(
            task.cancelled(), "Task shouldn't be cancelled on normal completion"
        )
        self.assertIsNone(
            task.exception(), "Task should have no exception on normal completion"
        )
        # Check that cleanup occurred via the callback
        self.assertNotIn(
            game_id,
            self.manager._schedulers,
            "Scheduler should be removed by callback",
        )
        self.assertNotIn(
            game_id,
            self.manager._scheduler_tasks,
            "Task should be removed by callback",
        )

    # Task completion callback on error is implicitly tested in test_create_scheduler_task_run_error_triggers_cleanup

    async def test_shutdown_multiple_schedulers(self):
        """Test shutting down the manager cancels and cleans up multiple active schedulers."""
        game_ids = ["game_shutdown_1", "game_shutdown_2"]
        tasks = []
        for gid in game_ids:
            # Give them some data to process so they stay active
            self._create_game_file(gid, [{"p": i} for i in range(5)])
            with (
                patch.object(self.manager, "_get_feeder_type", return_value="file"),
                self._patch_create_feeder(),
            ):
                scheduler, task = await self.manager.create_or_get_scheduler(gid)
                self.created_tasks_map[gid] = task
                tasks.append(task)
            await asyncio.sleep(0.01)  # Stagger start slightly

        # Verify initial state
        self.assertEqual(
            len(self.manager._schedulers),
            len(game_ids),
            "Incorrect number of schedulers before shutdown",
        )
        self.assertEqual(
            len(self.manager._scheduler_tasks),
            len(game_ids),
            "Incorrect number of tasks before shutdown",
        )
        for task in tasks:
            self.assertFalse(
                task.done(),
                f"Task {task.get_name()} should be active before shutdown",
            )

        # Perform shutdown
        await self.manager.shutdown()
        # Allow cancellations and cleanup tasks scheduled by shutdown to complete
        await asyncio.sleep(0.1)

        # Assert final state
        self.assertEqual(
            len(self.manager._schedulers),
            0,
            "Schedulers dict should be empty after shutdown",
        )
        self.assertEqual(
            len(self.manager._scheduler_tasks),
            0,
            "Tasks dict should be empty after shutdown",
        )
        for task in tasks:
            # Tasks should be cancelled by the shutdown process
            self.assertTrue(
                task.cancelled(),
                f"Task {task.get_name()} should be cancelled after shutdown",
            )

    async def test_shutdown_no_schedulers(self):
        """Test shutting down the manager when no schedulers are active."""
        self.assertEqual(
            len(self.manager._schedulers), 0, "Should be no schedulers initially"
        )
        self.assertEqual(
            len(self.manager._scheduler_tasks), 0, "Should be no tasks initially"
        )

        # Perform shutdown
        await self.manager.shutdown()
        await asyncio.sleep(0.01)  # Allow potential background tasks

        # Assert state remains empty
        self.assertEqual(
            len(self.manager._schedulers),
            0,
            "Schedulers should remain empty after shutdown",
        )
        self.assertEqual(
            len(self.manager._scheduler_tasks),
            0,
            "Tasks should remain empty after shutdown",
        )
        # No errors should have occurred

    async def test_concurrent_creation_same_game_uses_lock(self):
        """Test concurrent calls to create_or_get_scheduler for the same game_id are handled correctly by the lock."""
        game_id = "game_concurrent_create"
        self._create_game_file(game_id, [{"p": 1}])

        # --- Test Setup ---
        num_concurrent = 5
        # Use an event to signal when the first task has acquired the lock inside create_or_get_scheduler
        lock_acquired_event = asyncio.Event()
        # Use an event to hold back subsequent tasks until the first one is past the lock
        release_hold_event = asyncio.Event()

        # --- Patching Strategy ---
        # Patch the manager's internal lock's acquire method to add delay and signaling
        original_acquire = asyncio.Lock.acquire
        acquire_call_count = 0

        async def patched_acquire(lock_self):
            nonlocal acquire_call_count
            call_num = acquire_call_count + 1
            acquire_call_count = call_num
            # logging.debug(f"Task {asyncio.current_task().get_name()} attempting lock acquire (call #{call_num})...")

            if call_num == 1:
                # First task acquires the lock immediately but signals it has done so
                result = await original_acquire(lock_self)
                # logging.debug(f"Task {asyncio.current_task().get_name()} acquired lock (call #{call_num}), setting event.")
                lock_acquired_event.set()  # Signal that the lock is held
                # Hold inside the lock briefly to ensure others have to wait
                await asyncio.sleep(0.05)
                return result
            else:
                # Subsequent tasks wait for the first task to signal it has the lock
                # logging.debug(f"Task {asyncio.current_task().get_name()} waiting for lock_acquired_event (call #{call_num})...")
                await lock_acquired_event.wait()
                # Then they wait for the release signal before trying to acquire
                # logging.debug(f"Task {asyncio.current_task().get_name()} waiting for release_hold_event (call #{call_num})...")
                await release_hold_event.wait()
                # logging.debug(f"Task {asyncio.current_task().get_name()} proceeding to acquire lock (call #{call_num})...")
                # Now attempt the actual acquire (should block until first task releases)
                result = await original_acquire(lock_self)
                # logging.debug(f"Task {asyncio.current_task().get_name()} acquired lock (call #{call_num}).")
                return result

        # Define the concurrent task function
        async def create_concurrently(task_id: int):
            # Apply necessary patches within the coroutine that will run concurrently
            with (
                patch.object(self.manager, "_get_feeder_type", return_value="file"),
                self._patch_create_feeder(),
            ):
                # logging.debug(f"Concurrent task {task_id} starting create_or_get_scheduler")
                # The patched acquire will handle the synchronization
                return await self.manager.create_or_get_scheduler(game_id)

        # --- Execution ---
        # Apply the lock patch and run tasks concurrently
        with patch.object(asyncio.Lock, "acquire", patched_acquire):
            # Start all tasks
            concurrent_tasks = [
                asyncio.create_task(
                    create_concurrently(i), name=f"ConcurrentCreate_{i}"
                )
                for i in range(num_concurrent)
            ]

            # Wait until the first task signals it has acquired the lock
            await asyncio.wait_for(lock_acquired_event.wait(), timeout=1.0)
            # logging.debug("Lock acquired event set by first task.")

            # Now release the hold for other tasks to proceed and contend for the lock
            # logging.debug("Setting release hold event.")
            release_hold_event.set()

            # Wait for all concurrent tasks to complete
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            # logging.debug(f"Concurrent tasks finished. Results: {results}")

        # --- Assertions ---
        # Check for exceptions in results
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                self.fail(f"Concurrent task {i} failed with exception: {res}")

        self.assertEqual(
            len(results),
            num_concurrent,
            "Should have results from all concurrent calls",
        )

        # Check that all results point to the *same* scheduler and task instance
        first_scheduler, first_task = results[0]
        self.assertIsNotNone(first_scheduler)
        self.assertIsNotNone(first_task)
        self.created_tasks_map[game_id] = first_task  # Store for cleanup check

        for i in range(1, num_concurrent):
            scheduler_i, task_i = results[i]
            self.assertIs(
                scheduler_i,
                first_scheduler,
                f"Scheduler from call {i + 1} should be the same as the first",
            )
            self.assertIs(
                task_i,
                first_task,
                f"Task from call {i + 1} should be the same as the first",
            )

        # Verify internal state of the manager - only ONE instance should exist
        self.assertEqual(
            len(self.manager._schedulers),
            1,
            "Manager should only store one scheduler instance due to lock",
        )
        self.assertEqual(
            len(self.manager._scheduler_tasks),
            1,
            "Manager should only store one task instance due to lock",
        )
        self.assertIs(
            self.manager._schedulers[game_id],
            first_scheduler,
            "Stored scheduler should be the one returned by all",
        )


# Allow running the tests directly
if __name__ == "__main__":
    unittest.main()
