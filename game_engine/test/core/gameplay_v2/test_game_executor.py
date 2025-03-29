import unittest
from unittest import skip
from unittest.mock import MagicMock, patch
from concurrent.futures import Future
from src.core.gameplay.game_executor import GameExecutionManager
from game_engine.src.core.gameplay.game_data_fetcher import GameLifecycleManager
from src.core.gameplay.game_play import GamePlay


class TestGameExecutionManager(unittest.TestCase):
    def setUp(self):
        self.mock_lifecycle_manager = MagicMock(spec=GameLifecycleManager)
        self.executor = GameExecutionManager(self.mock_lifecycle_manager, max_workers=2)
        # Mock GamePlay objects
        self.mock_gameplay = MagicMock(spec=GamePlay)
        self.mock_gameplay.game_id = "game_1"

    def tearDown(self):
        self.executor.shutdown()

    def test_run_game_schedules_game(self):
        """Test that run_game schedules a game and adds it to running_games."""
        with patch.object(self.executor, "_run_game_thread") as mock_run_game_thread:
            with patch.object(self.executor.executor, "submit") as mock_submit:
                future = Future()
                mock_submit.return_value = future
                self.executor.run_game(self.mock_gameplay)

                self.assertIn("game_1", self.executor.running_games)
                mock_submit.assert_called_once_with(
                    mock_run_game_thread, self.mock_gameplay
                )

    def test_run_game_prevents_duplicate_scheduling(self):
        """Test that trying to run a game that's already running raises an exception."""
        with patch.object(self.executor.executor, "submit", return_value=Future()):
            self.executor.run_game(self.mock_gameplay)

            # Attempt to run the same game again
            with self.assertRaises(ValueError) as context:
                self.executor.run_game(self.mock_gameplay)

            self.assertEqual(str(context.exception), "Game game_1 is already running.")

    def test_on_game_finished_removes_game_from_running(self):
        """Test that _on_game_finished removes the game from running_games."""
        future = Future()
        future.set_result(None)  # Simulate successful completion
        self.executor.running_games["game_1"] = future

        self.executor._on_game_finished(future)

        self.assertNotIn("game_1", self.executor.running_games)
        self.mock_lifecycle_manager.remove_game.assert_called_once_with("game_1")

    @skip("Logs are Yet to be Implemented")
    def test_on_game_finished_handles_exceptions(self):
        """Test that _on_game_finished handles exceptions in game execution."""
        future = Future()
        future.set_exception(Exception("Game error"))  # Simulate an exception
        self.executor.running_games["game_1"] = future

        self.executor._on_game_finished(future)

        with self.assertLogs() as log:
            self.executor._on_game_finished(future)

        self.assertIn(
            "Exception occurred for game in thread: Game error", log.output[-1]
        )
        self.assertNotIn("game_1", self.executor.running_games)

    def test_run_game_thread_executes_gameplay(self):
        """Test that _run_game_thread invokes gameplay.run."""
        self.executor._run_game_thread(self.mock_gameplay)
        self.mock_gameplay.run.assert_called_once()

    def test_shutdown_stops_all_threads(self):
        """Test that shutdown waits for all threads to complete."""
        with patch.object(self.executor.executor, "shutdown") as mock_shutdown:
            self.executor.shutdown()
            mock_shutdown.assert_called_once_with(wait=True)

    def test_thread_safety_with_multiple_games(self):
        """Test thread safety when scheduling multiple games."""
        mock_gameplay2 = MagicMock(spec=GamePlay)
        mock_gameplay2.game_id = "game_2"

        # Use an Event to simulate the long-running task and prevent it from finishing immediately
        def mock_run_game_thread(gameplay: GamePlay):
            import time

            # Simulate a long-running game by adding a delay
            time.sleep(0.2)
            gameplay.run()

        with patch.object(
            self.executor, "_run_game_thread", side_effect=mock_run_game_thread
        ):
            # Run the first game
            self.executor.run_game(self.mock_gameplay)
            # Run the second game while the first one is still running
            self.executor.run_game(mock_gameplay2)

            # Assert that both games are scheduled and running concurrently
            self.assertIn("game_1", self.executor.running_games)
            self.assertIn("game_2", self.executor.running_games)

            from time import sleep

            sleep(0.3)
            # Assert that the first game is removed from running_games
            self.assertNotIn("game_1", self.executor.running_games)

            # Assert that the second game is removed from running_games
            self.assertNotIn("game_2", self.executor.running_games)

    @skip("Logs are Yet to be Implemented")
    def test_run_game_handles_execution_exception(self):
        """Test that exceptions raised during gameplay are logged."""
        self.mock_gameplay.run.side_effect = Exception("Execution failure")

        with self.assertLogs() as log:
            self.executor._run_game_thread(self.mock_gameplay)

        self.assertIn("Error in game game_1: Execution failure", log.output[-1])

    def test_run_game_callback_removal_on_completion(self):
        """Test that the future callback removes the game on completion."""
        with patch.object(self.executor.executor, "submit") as mock_submit:
            future = Future()
            mock_submit.return_value = future

            self.executor.run_game(self.mock_gameplay)

            # Verify callback is set
            self.assertEqual(future._done_callbacks[0].__self__, self.executor)
