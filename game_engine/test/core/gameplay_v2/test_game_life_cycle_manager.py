import unittest
from unittest.mock import MagicMock
from game_engine.src.core.gameplay.game_data_fetcher import GameLifecycleManager
from src.core.gameplay.game_play import GamePlay


class TestGameLifecycleManager(unittest.TestCase):
    def setUp(self):
        # Setup for each test
        self.lifecycle_manager = GameLifecycleManager()
        self.mock_game = MagicMock(spec=GamePlay)
        self.mock_game.game_id = "game_1"

    def test_add_game(self):
        """Test adding a game to the lifecycle manager."""
        self.lifecycle_manager.add_game(self.mock_game)
        self.assertIn("game_1", self.lifecycle_manager.games)
        self.assertEqual(self.lifecycle_manager.games["game_1"], self.mock_game)

    def test_remove_game(self):
        """Test removing a game from the lifecycle manager."""
        self.lifecycle_manager.add_game(self.mock_game)
        self.lifecycle_manager.remove_game("game_1")
        self.assertNotIn("game_1", self.lifecycle_manager.games)

    def test_remove_non_existent_game(self):
        """Test removing a game that does not exist."""
        self.lifecycle_manager.remove_game("non_existent_game")
        self.assertEqual(len(self.lifecycle_manager.games), 0)  # Ensure no errors occur

    def test_get_game(self):
        """Test retrieving a game by its ID."""
        self.lifecycle_manager.add_game(self.mock_game)
        game = self.lifecycle_manager.get_game("game_1")
        self.assertEqual(game, self.mock_game)

    def test_get_non_existent_game(self):
        """Test retrieving a game that does not exist."""
        game = self.lifecycle_manager.get_game("non_existent_game")
        self.assertIsNone(game)

    def test_stop_all_games(self):
        """Test signaling all games to stop."""
        mock_game_2 = MagicMock(spec=GamePlay)
        mock_game_2.game_id = "game_2"

        self.lifecycle_manager.add_game(self.mock_game)
        self.lifecycle_manager.add_game(mock_game_2)

        self.lifecycle_manager.stop_all_games()

        self.mock_game.stop.assert_called_once_with(None)
        mock_game_2.stop.assert_called_once_with(None)

    def test_shutdown_all(self):
        """Test clearing all active games."""
        self.lifecycle_manager.add_game(self.mock_game)
        self.assertIn("game_1", self.lifecycle_manager.games)  # Verify game exists

        self.lifecycle_manager.shutdown_all()
        self.assertEqual(len(self.lifecycle_manager.games), 0)
