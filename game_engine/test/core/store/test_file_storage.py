import unittest
import json
import os
import tempfile
from src.store.file_storage import FileStorage
from src.store.game_data import GameData, TeamData, PlayerData


class TestFileStorage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """Create a temporary directory for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = FileStorage(self.temp_dir.name)
        print(self.storage.directory)
        self.game_data = GameData(
            game_id="game123",
            teams={
                "team_1": TeamData(name="Team A", players=[PlayerData(name="Player 1")]),
                "team_2": TeamData(name="Team B", players=[PlayerData(name="Player 2")]),
            },
        )

    def tearDown(self):
        """Clean up temporary directory after test execution."""
        self.temp_dir.cleanup()

    async def test_store_game_data_creates_file(self):
        """Test that store_game_data correctly writes data to a file"""
        file_path = self.storage.get_file_path(self.game_data.game_id)

        await self.storage.store_game_data(self.game_data)

        # Verify that the file exists and contains the correct data
        self.assertTrue(os.path.exists(file_path))

        with open(file_path, "r") as file:
            stored_data = json.load(file)
        
        self.assertEqual(stored_data["teams"]["team_1"]["name"], "Team A")
        self.assertEqual(stored_data["teams"]["team_2"]["name"], "Team B")

    async def test_append_score_to_existing_file(self):
        """Test appending a score to an existing game file"""
        file_path = self.storage.get_file_path("game123")

        # First, store the initial game data
        await self.storage.store_game_data(self.game_data)

        # Append score
        score_data = {"team_1": 10, "team_2": 15}
        await self.storage.append_score("game123", score_data)

        # Read back the file
        with open(file_path, "r") as file:
            game_data = json.load(file)

        self.assertIn("scores", game_data)
        self.assertEqual(game_data["scores"], [score_data])

    async def test_append_score_to_new_game(self):
        """Test that append_score initializes a new file if it doesn't exist"""
        print(self.storage.directory)
        file_path = self.storage.get_file_path("new_game")
        # print(file_path)
        # Ensure file does not exist before appending
        self.assertFalse(os.path.exists(file_path))

        score_data = {"team_1": 5, "team_2": 10}
        await self.storage.append_score("new_game", score_data)

        # Now file should exist
        self.assertTrue(os.path.exists(file_path))

        # Read data
        with open(file_path, "r") as file:
            game_data = json.load(file)

        self.assertEqual(game_data["scores"], [score_data])

    async def test_append_score_keeps_existing_scores(self):
        """Test that scores are correctly appended without overwriting"""
        file_path = self.storage.get_file_path("game123")

        await self.storage.store_game_data(self.game_data)

        # Append first score
        score1 = {"team_1": 10, "team_2": 15}
        await self.storage.append_score("game123", score1)

        # Append second score
        score2 = {"team_1": 20, "team_2": 25}
        await self.storage.append_score("game123", score2)

        # Read back data
        with open(file_path, "r") as file:
            game_data = json.load(file)

        self.assertEqual(len(game_data["scores"]), 2)
        self.assertIn(score1, game_data["scores"])
        self.assertIn(score2, game_data["scores"])

    async def test_append_score_handles_corrupt_file(self):
        """Test that append_score handles a corrupted file gracefully"""
        file_path = self.storage.get_file_path("corrupt_game")

        # Write a corrupted JSON file
        with open(file_path, "w") as file:
            file.write("{invalid_json}")

        score_data = {"team_1": 5, "team_2": 10}

        with self.assertRaises(json.JSONDecodeError):
            await self.storage.append_score("corrupt_game", score_data)
