import unittest
from unittest.mock import MagicMock, patch
from src.core.gameplay.game_controller import GameController
from src.core.models.events import EventAggregator
from src.core.models.events.game import GameEventType
from src.core.gameplay.game_play import GamePlay
from game_engine.src.core.gameplay.game_data_fetcher import GameLifecycleManager
from src.core.gameplay.game_event_dispatcher import GameEventDispatcher
from src.core.gameplay.game_executor import GameExecutionManager


class TestGameController(unittest.TestCase):

    def setUp(self):
        # Create mocks for dependencies
        self.mock_event_aggregator = MagicMock(spec=EventAggregator)
        self.mock_lifecycle_manager = MagicMock(spec=GameLifecycleManager)
        self.mock_execution_manager = MagicMock(spec=GameExecutionManager)
        self.mock_event_dispatcher = MagicMock(spec=GameEventDispatcher)

        # Instantiate the GameController with mock dependencies
        self.controller = GameController(
            event_aggregator=self.mock_event_aggregator,
            lifecycle_manager=self.mock_lifecycle_manager,
            execution_manager=self.mock_execution_manager,
            event_dispatcher=self.mock_event_dispatcher,
        )

        # Mock GamePlay object
        self.mock_gameplay = MagicMock(spec=GamePlay)
        self.mock_gameplay.game_id = "game_1"

    def tearDown(self):
        pass

    def test_schedule_game_calls_lifecycle_manager_add_game(self):
        """Test that schedule_game calls add_game on the lifecycle manager."""
        self.controller.schedule_game(self.mock_gameplay)

        self.mock_lifecycle_manager.add_game.assert_called_once_with(self.mock_gameplay)

    def test_schedule_game_calls_event_dispatcher_subscribe(self):
        """Test that schedule_game calls subscribe_to_game_events on the event dispatcher."""
        events = [GameEventType.START, GameEventType.STOP]
        self.controller.schedule_game(self.mock_gameplay, events)

        self.mock_event_dispatcher.subscribe_to_game_events.assert_called_once_with(
            self.mock_gameplay, events
        )

    def test_schedule_game_calls_execution_manager_run_game(self):
        """Test that schedule_game calls run_game on the execution manager."""
        self.controller.schedule_game(self.mock_gameplay)

        self.mock_execution_manager.run_game.assert_called_once_with(self.mock_gameplay)

    def test_shutdown_calls_lifecycle_manager_stop_all_games(self):
        """Test that shutdown calls stop_all_games on the lifecycle manager."""
        self.controller.shutdown()

        self.mock_lifecycle_manager.stop_all_games.assert_called_once()

    def test_shutdown_calls_execution_manager_shutdown(self):
        """Test that shutdown calls shutdown on the execution manager."""
        self.controller.shutdown()

        self.mock_execution_manager.shutdown.assert_called_once()

    def test_shutdown_calls_lifecycle_manager_shutdown_all(self):
        """Test that shutdown calls shutdown_all on the lifecycle manager."""
        self.controller.shutdown()

        self.mock_lifecycle_manager.shutdown_all.assert_called_once()

    def test_schedule_game_without_events(self):
        """Test that schedule_game works without events."""
        self.controller.schedule_game(self.mock_gameplay)

        # Ensure that lifecycle manager and execution manager are still called correctly
        self.mock_lifecycle_manager.add_game.assert_called_once_with(self.mock_gameplay)
        self.mock_execution_manager.run_game.assert_called_once_with(self.mock_gameplay)

    def test_schedule_game_with_default_lifecycle_manager_and_execution_manager(self):
        """Test that the GameController uses default lifecycle manager and execution manager if not provided."""
        controller = GameController(self.mock_event_aggregator)

        controller.schedule_game(self.mock_gameplay)

        # Ensure that default lifecycle manager and execution manager are used
        self.assertIsInstance(controller.lifecycle_manager, GameLifecycleManager)
        self.assertIsInstance(controller.execution_manager, GameExecutionManager)
