# test/app/websockets/scheduler/test_scheduler.py (Create this new file)

import unittest
import tempfile
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock # We'll need AsyncMock

# Adjust imports based on your project structure
from backend.app.scheduler.scheduler import GameScheduler, BaseScheduler
from backend.app.scheduler.game_feeder import FileGameFeeder
from db.file_storage import BackendFileStorage
from backend.app.broker.InMemoryMessageBroker import InMemoryMessageBroker
from backend.app.shared.enums.broker_channels import BrokerChannels

# Helper from broker tests - copy or import if accessible
async def consume_messages(generator: asyncio.StreamReader, count: int, timeout: float = 1.0) -> list:
    messages = []
    for _ in range(count):
        try:
            message = await asyncio.wait_for(generator.__anext__(), timeout=timeout)
            messages.append(message.get("data"))
        except (StopAsyncIteration, asyncio.TimeoutError) as e:
            # Re-raise TimeoutError to signal timeout, otherwise break loop
            if isinstance(e, asyncio.TimeoutError):
                raise e
            break # StopAsyncIteration means generator finished
    return messages


# --- Test Data ---
TEST_GAME_ID_SCHED = "game_sched_123"
# Use a smaller, manageable list for scheduler tests
TEST_SCORES_LIST_SCHED = [
    {"set": [[0], [0]], "game_points": [1, 0]},
    {"set": [[0], [0]], "game_points": [1, 1]},
    {"set": [[0], [0]], "game_points": [1, 2]},
    {"set": [[0], [0]], "game_points": [1, 3]},
]
TEST_GAME_DATA_SCHED = {
    "game_id": TEST_GAME_ID_SCHED,
    "teams": {"team_1": {"name": "P1"}, "team_2": {"name": "P2"}},
    "scores": TEST_SCORES_LIST_SCHED
}
# --- End Test Data ---

class TestGameScheduler(unittest.IsolatedAsyncioTestCase):
    """Test suite for the GameScheduler class."""

    async def asyncSetUp(self):
        """Set up dependencies: temp dir, storage, feeder, broker, scheduler."""
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir_obj.name)

        # Setup File Storage and Data
        self.storage_base_path = self.temp_dir_path / "data" / "games"
        self.storage_base_path.mkdir(parents=True, exist_ok=True)
        self.test_file_path = self.storage_base_path / f"{TEST_GAME_ID_SCHED}.json"
        with open(self.test_file_path, 'w') as f:
            json.dump(TEST_GAME_DATA_SCHED, f)

        self.storage = BackendFileStorage(base_path=str(self.storage_base_path))
        # Use the real FileGameFeeder
        self.feeder = FileGameFeeder(game_id=TEST_GAME_ID_SCHED, storage=self.storage)
        # Use the real InMemoryMessageBroker
        self.broker = InMemoryMessageBroker()

        # Instantiate the scheduler
        self.scheduler = GameScheduler(
            game_id=TEST_GAME_ID_SCHED,
            broker=self.broker,
            feeder=self.feeder,
            game_speed=0.1 # Set a faster speed for testing
        )
        # Keep track of the main run task
        self.scheduler_task: asyncio.Task | None = None

    async def asyncTearDown(self):
        """Clean up resources: cancel task, shutdown broker, remove temp dir."""
        # Ensure the scheduler task is cancelled and awaited
        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
            try:
                await asyncio.wait_for(self.scheduler_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass # Expected exceptions on cancellation/timeout
            except Exception as e:
                 print(f"Error during scheduler task cleanup: {e}") # Log other errors

        # Shutdown broker
        await self.broker.shutdown()
        # Cleanup temp dir
        self.temp_dir_obj.cleanup()

    def test_initialization(self):
        """Test correct initialization of GameScheduler."""
        self.assertIsInstance(self.scheduler, BaseScheduler)
        self.assertEqual(self.scheduler.game_id, TEST_GAME_ID_SCHED)
        self.assertEqual(self.scheduler.broker, self.broker)
        self.assertEqual(self.scheduler.feeder, self.feeder)
        self.assertEqual(self.scheduler.speed, 0.1)
        self.assertFalse(self.scheduler.pause_event.is_set(), "Scheduler should be paused initially")
        self.assertIsNone(self.scheduler._current_sleep)
        self.assertIn('start', self.scheduler.controls)
        self.assertIn('pause', self.scheduler.controls)
        self.assertIn('resume', self.scheduler.controls)
        self.assertIn('adjust_speed', self.scheduler.controls)

    async def test_run_publishes_scores_when_started(self):
        """Test that run() publishes scores from feeder after start()."""
        # Subscribe to the scores channel *before* starting
        score_subscriber = self.broker.subscribe(TEST_GAME_ID_SCHED, BrokerChannels.SCORES_UPDATE)
        await asyncio.sleep(0.01) # Allow subscription

        # Start the scheduler in the background
        self.scheduler_task = asyncio.create_task(self.scheduler.run())
        await asyncio.sleep(0.01) # Allow task to start listening

        # Start the game flow
        await self.scheduler.start()
        self.assertTrue(self.scheduler.pause_event.is_set())

        # Consume the expected number of scores
        # Use a longer timeout accounting for default speed=1.0
        timeout_per_message = self.scheduler.speed + 0.1 # Base timeout + buffer
        total_timeout = len(TEST_SCORES_LIST_SCHED) * timeout_per_message
        received_scores = await consume_messages(score_subscriber, len(TEST_SCORES_LIST_SCHED), timeout=total_timeout)

        # Assertions
        self.assertListEqual(received_scores, TEST_SCORES_LIST_SCHED)

        # Wait for the scheduler task to complete naturally (feeder exhausted)
        await asyncio.wait_for(self.scheduler_task, timeout=1.0) # Should finish quickly after last score
        self.assertTrue(self.scheduler_task.done())
        self.assertIsNone(self.scheduler_task.exception()) # Check for errors in the task

    async def test_pause_and_resume(self):
        """Test pausing and resuming score publication."""
        score_subscriber = self.broker.subscribe(TEST_GAME_ID_SCHED, BrokerChannels.SCORES_UPDATE)
        await asyncio.sleep(0.01)

        self.scheduler_task = asyncio.create_task(self.scheduler.run())
        await asyncio.sleep(0.01)

        # Start and consume one score
        await self.scheduler.start()
        received1 = await consume_messages(score_subscriber, 1, timeout=self.scheduler.speed + 0.5)
        self.assertEqual(len(received1), 1)
        self.assertEqual(received1[0], TEST_SCORES_LIST_SCHED[0])

        # Pause
        await self.scheduler.pause()
        self.assertFalse(self.scheduler.pause_event.is_set())

        # Try to consume another score - should time out
        with self.assertRaises(asyncio.TimeoutError):
            await consume_messages(score_subscriber, 1, timeout=0.2) # Short timeout

        # Needs to resubsribe as the previous subscriber/generator terminated because of the error raised
        score_subscriber = self.broker.subscribe(TEST_GAME_ID_SCHED, BrokerChannels.SCORES_UPDATE)
        # Resume
        await self.scheduler.resume()
        self.assertTrue(self.scheduler.pause_event.is_set())

        # Consume remaining scores
        remaining_count = len(TEST_SCORES_LIST_SCHED) - 1
        timeout_per_message = self.scheduler.speed + 0.1
        total_timeout = remaining_count * timeout_per_message
        received_remaining = await consume_messages(score_subscriber, remaining_count, timeout=total_timeout)

        self.assertEqual(len(received_remaining), remaining_count)
        self.assertListEqual(received_remaining, TEST_SCORES_LIST_SCHED[1:])

        # Wait for completion
        await asyncio.wait_for(self.scheduler_task, timeout=1.0)
        self.assertTrue(self.scheduler_task.done())

    async def test_adjust_speed(self):
        """Test adjusting the speed between score publications."""
        new_speed = 0.05 # Much faster
        score_subscriber = self.broker.subscribe(TEST_GAME_ID_SCHED, BrokerChannels.SCORES_UPDATE)
        await asyncio.sleep(0.01)

        self.scheduler_task = asyncio.create_task(self.scheduler.run())
        await asyncio.sleep(0.01)

        # Start and consume one score at default speed
        await self.scheduler.start()
        await consume_messages(score_subscriber, 1, timeout=self.scheduler.speed + 0.1)

        # Adjust speed
        await self.scheduler.adjust_speed(new_speed)
        self.assertEqual(self.scheduler.speed, new_speed)

        # Consume remaining scores - should be faster now
        remaining_count = len(TEST_SCORES_LIST_SCHED) - 1
        # Use a timeout based on the *new* speed
        timeout_per_message = new_speed + 0.1 # New speed + buffer
        total_timeout = remaining_count * timeout_per_message
        start_time = asyncio.get_event_loop().time()
        received_remaining = await consume_messages(score_subscriber, remaining_count, timeout=total_timeout)
        end_time = asyncio.get_event_loop().time()

        # Assertions
        self.assertEqual(len(received_remaining), remaining_count)
        self.assertListEqual(received_remaining, TEST_SCORES_LIST_SCHED[1:])
        # Check if time taken is roughly consistent with the new speed
        # This is an approximate check
        expected_time_min = remaining_count * new_speed
        self.assertLess(end_time - start_time, expected_time_min + 0.1, "Scores did not arrive faster after speed adjustment")

        # Wait for completion
        await asyncio.wait_for(self.scheduler_task, timeout=1.0)
        self.assertTrue(self.scheduler_task.done())

    async def test_control_messages(self):
        """Test receiving and handling control messages via the broker."""
        score_subscriber = self.broker.subscribe(TEST_GAME_ID_SCHED, BrokerChannels.SCORES_UPDATE)
        await asyncio.sleep(0.01)

        self.scheduler_task = asyncio.create_task(self.scheduler.run())
        await asyncio.sleep(0.01) # Allow scheduler run() to start and subscribe

        # 1. Send 'start' control
        await self.broker.publish(TEST_GAME_ID_SCHED, BrokerChannels.CONTROLS, {"type": "start"})
        await asyncio.sleep(0.05) # Allow control message processing
        self.assertTrue(self.scheduler.pause_event.is_set())
        # Consume one score to verify start
        received1 = await consume_messages(score_subscriber, 1, timeout=self.scheduler.speed + 0.5)
        self.assertEqual(len(received1), 1)

        # 2. Send 'pause' control
        await self.broker.publish(TEST_GAME_ID_SCHED, BrokerChannels.CONTROLS, {"type": "pause"})
        await asyncio.sleep(0.05)
        self.assertFalse(self.scheduler.pause_event.is_set())
        # Verify pause by timeout
        with self.assertRaises(asyncio.TimeoutError):
            await consume_messages(score_subscriber, 1, timeout=0.2)

        # 3. Send 'adjust_speed' control
        new_speed = 0.05
        await self.broker.publish(TEST_GAME_ID_SCHED, BrokerChannels.CONTROLS, {"type": "adjust_speed", "speed": new_speed})
        await asyncio.sleep(0.05)
        self.assertEqual(self.scheduler.speed, new_speed)

        # re-subscribe as the previous generator is terminated 
        score_subscriber = self.broker.subscribe(TEST_GAME_ID_SCHED, BrokerChannels.SCORES_UPDATE)

        # 4. Send 'resume' control
        await self.broker.publish(TEST_GAME_ID_SCHED, BrokerChannels.CONTROLS, {"type": "resume"})
        await asyncio.sleep(0.05)
        self.assertTrue(self.scheduler.pause_event.is_set())
        
        # Consume remaining scores quickly
        remaining_count = len(TEST_SCORES_LIST_SCHED) - 1
        timeout_per_message = new_speed + 0.2
        total_timeout = remaining_count * timeout_per_message
        received_remaining = await consume_messages(score_subscriber, remaining_count, timeout=total_timeout)
        self.assertEqual(len(received_remaining), remaining_count)

        # Wait for completion
        await asyncio.wait_for(self.scheduler_task, timeout=1.0)
        self.assertTrue(self.scheduler_task.done())

    async def test_feeder_cleanup_called_on_completion(self):
        """Verify feeder.cleanup() is called when the scheduler run finishes."""
        # Mock the feeder's cleanup method
        self.feeder.cleanup = AsyncMock() # Replace with an async mock

        # Re-instantiate scheduler with the mocked feeder
        self.scheduler = GameScheduler(
            game_id=TEST_GAME_ID_SCHED,
            broker=self.broker,
            feeder=self.feeder, # Now has mocked cleanup
            game_speed=0.1
        )

        # Run the scheduler to completion
        self.scheduler_task = asyncio.create_task(self.scheduler.run())
        await asyncio.sleep(0.01)
        await self.scheduler.start()
        # Wait for the task to finish (adjust timeout if needed based on speed/data size)
        await asyncio.wait_for(self.scheduler_task, timeout=len(TEST_SCORES_LIST_SCHED) * (self.scheduler.speed + 0.1))

        # Assert cleanup was called
        self.feeder.cleanup.assert_awaited_once()
