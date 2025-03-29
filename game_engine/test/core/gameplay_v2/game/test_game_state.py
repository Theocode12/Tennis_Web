import unittest
from unittest.mock import patch, MagicMock
from game_engine.src.core.gameplay.game.match_type import (
    MatchType,
)  # Assuming it might be used in a larger context
from threading import Event
from src.core.gameplay.game.game_state import (
    GameState,
)  # Replace `your_module_path` with the actual path


class TestGameState(unittest.TestCase):
    def setUp(self):
        self.game_state = GameState()

    def test_initial_state(self):
        # Ensure the initial state is correct
        self.assertTrue(
            self.game_state.is_running(), "Game should initially be running"
        )
        self.assertFalse(
            self.game_state._state.is_set(), "Initial state should not be set"
        )

    def test_wait_for_state_change(self):
        with patch.object(
            self.game_state._state, "wait", return_value=None
        ) as mock_wait:
            self.game_state.wait_for_state_change()
            mock_wait.assert_called_once()

    def test_start(self):
        self.game_state.start(None)
        self.assertTrue(
            self.game_state._state.is_set(), "State should be set after start"
        )

    def test_stop(self):
        self.game_state.stop(None)
        self.assertFalse(
            self.game_state.is_running(), "Game should not be running after stop"
        )
        self.assertTrue(
            self.game_state._state.is_set(), "State should be set after stop"
        )

    def test_pause(self):
        self.game_state.start(None)  # Set state to true before pausing
        self.game_state.pause(None)
        self.assertFalse(
            self.game_state._state.is_set(), "State should be cleared after pause"
        )

    def test_resume(self):
        self.game_state.pause(None)  # Clear state before resuming
        self.game_state.resume(None)
        self.assertTrue(
            self.game_state._state.is_set(), "State should be set after resume"
        )
