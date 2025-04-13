import unittest
import tempfile
import json
import asyncio
from pathlib import Path
from collections import deque

# Adjust imports based on your project structure
from backend.app.scheduler.game_feeder import FileGameFeeder, BaseGameFeeder
from db.file_storage import BackendFileStorage # Assuming this path is correct

# --- Define the test data using the ACTUAL structure ---
TEST_GAME_ID = "test_123"
# Use the actual score structure from the provided JSON
TEST_SCORES_LIST = [
    {"set": [[0], [0]], "game_points": [1, 0]},
    {"set": [[0], [0]], "game_points": [1, 1]},
    {"set": [[0], [0]], "game_points": [1, 2]},
    {"set": [[0], [0]], "game_points": [1, 3]},
    {"set": [[0], [0]], "game_points": [2, 3]},
    {"set": [[0], [0]], "game_points": [3, 3]},
    {"set": [[0], [0]], "game_points": [3, 4]},
    {"set": [[0], [0]], "game_points": [3, 5]},
    {"set": [[0], [1]], "game_points": [0, 1]},
]

# The full structure expected in the JSON file
TEST_GAME_DATA = {
    "game_id": TEST_GAME_ID,
    "teams": { # Include teams for completeness, though feeder only uses scores
        "team_1": {"name": "Team A", "players": [{"name": "Alice"}]},
        "team_2": {"name": "Team B", "players": [{"name": "Bob"}]}
    },
    "scores": TEST_SCORES_LIST
}
# --- End of test data definition ---


class TestFileGameFeeder(unittest.IsolatedAsyncioTestCase):
    """Test suite for the FileGameFeeder class."""

    def setUp(self):
        """Set up a temporary directory and the test game data file."""
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir_obj.name)

        self.storage_base_path = self.temp_dir_path / "data" / "games"
        self.storage_base_path.mkdir(parents=True, exist_ok=True)

        self.test_file_path = self.storage_base_path / f"{TEST_GAME_ID}.json"
        # Write the full game data structure to the file
        with open(self.test_file_path, 'w') as f:
            json.dump(TEST_GAME_DATA, f) # Use the full structure

        self.storage = BackendFileStorage(base_path=str(self.storage_base_path))
        self.feeder = FileGameFeeder(game_id=TEST_GAME_ID, storage=self.storage)

    def tearDown(self):
        """Clean up the temporary directory."""
        self.temp_dir_obj.cleanup()

    def test_initialization(self):
        """Test correct initialization of FileGameFeeder."""
        self.assertIsInstance(self.feeder, BaseGameFeeder)
        self.assertEqual(self.feeder.game_id, TEST_GAME_ID)
        self.assertEqual(self.feeder.storage, self.storage)
        expected_path = self.storage.get_game_path(TEST_GAME_ID)
        self.assertEqual(self.feeder.file_path, expected_path)
        self.assertEqual(self.feeder.file_path, self.test_file_path)
        self.assertIsInstance(self.feeder._buffer, deque)
        self.assertEqual(len(self.feeder._buffer), 0)
        self.assertFalse(self.feeder._exhausted)

    async def test_load_batch_populates_buffer_and_exhausts(self):
        """Test that _load_batch (called via get_next_score) loads all data and sets exhausted."""
        self.assertFalse(self.feeder._exhausted)
        self.assertEqual(len(self.feeder._buffer), 0)

        score_iterator = self.feeder.get_next_score()
        first_score = await score_iterator.__anext__()

        # Compare with the first item from the correct list
        self.assertEqual(first_score, TEST_SCORES_LIST[0])
        self.assertTrue(self.feeder._exhausted, "Feeder should be exhausted after loading from file")
        self.assertEqual(len(self.feeder._buffer), len(TEST_SCORES_LIST) - 1)
        # Check buffer contains the rest of the items
        expected_remaining = deque(TEST_SCORES_LIST[1:])
        self.assertEqual(self.feeder._buffer, expected_remaining)

    async def test_get_next_score_yields_all_scores_in_order(self):
        """Test iterating through all scores using get_next_score."""
        collected_scores = []
        score_iterator = self.feeder.get_next_score()
        async for score in score_iterator:
            collected_scores.append(score)

        self.assertEqual(len(collected_scores), len(TEST_SCORES_LIST))
        # Compare with the correct list
        self.assertListEqual(collected_scores, TEST_SCORES_LIST)
        self.assertTrue(self.feeder._exhausted)
        self.assertEqual(len(self.feeder._buffer), 0)

    async def test_get_next_score_stops_after_exhaustion(self):
        """Test that StopAsyncIteration is raised after all scores are yielded."""
        score_iterator = self.feeder.get_next_score()
        async for _ in score_iterator:
            pass
        with self.assertRaises(StopAsyncIteration):
            await score_iterator.__anext__()
        self.assertTrue(self.feeder._exhausted)
        self.assertEqual(len(self.feeder._buffer), 0)

    async def test_load_batch_file_not_found(self):
        """Test behavior when the game data file does not exist."""
        non_existent_game_id = "game_not_found_404"
        feeder_no_file = FileGameFeeder(game_id=non_existent_game_id, storage=self.storage)
        self.assertFalse(feeder_no_file.file_path.exists())

        score_iterator = feeder_no_file.get_next_score()
        with self.assertRaises(FileNotFoundError):
            await score_iterator.__anext__()
        self.assertTrue(feeder_no_file._exhausted)
        self.assertEqual(len(feeder_no_file._buffer), 0)

    async def test_cleanup_clears_buffer(self):
        """Test the cleanup method inherited/implemented."""
        score_iterator = self.feeder.get_next_score()
        await score_iterator.__anext__() # Load the data
        self.assertNotEqual(len(self.feeder._buffer), 0)

        await self.feeder.cleanup()
        self.assertEqual(len(self.feeder._buffer), 0)

# Allow running the tests directly
if __name__ == '__main__':
    unittest.main()
