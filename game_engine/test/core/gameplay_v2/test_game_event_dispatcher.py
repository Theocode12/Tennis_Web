import unittest
from unittest.mock import MagicMock
from src.core.gameplay.game_event_dispatcher import GameEventDispatcher
from game_engine.src.core.gameplay.game_data_fetcher import GameLifecycleManager
from src.core.gameplay.game_play import GamePlay
from src.core.models.events import EventAggregator
from src.core.models.events.game import GameEventType, GameEventPayload


class TestGameEventDispatcher(unittest.TestCase):
    def setUp(self):
        # Set up the mocks and objects
        self.mock_event_aggregator = MagicMock(spec=EventAggregator)
        self.mock_lifecycle_manager = MagicMock(spec=GameLifecycleManager)
        self.dispatcher = GameEventDispatcher(
            self.mock_event_aggregator, self.mock_lifecycle_manager
        )

        self.mock_gameplay = MagicMock(spec=GamePlay)
        self.mock_gameplay.game_id = "game_1"

    def test_subscribe_to_game_events_with_defaults(self):
        """Test subscribing to default events."""
        self.dispatcher.subscribe_to_game_events(self.mock_gameplay)
        default_events = [
            GameEventType.START,
            GameEventType.STOP,
            GameEventType.PAUSE,
            GameEventType.RESUME,
        ]
        self.mock_gameplay.subscribe_to_events.assert_called_once_with(
            default_events, self.mock_event_aggregator
        )

    def test_subscribe_to_game_events_with_custom_events(self):
        """Test subscribing to custom events."""
        custom_events = [GameEventType.START, GameEventType.FINISH]
        self.dispatcher.subscribe_to_game_events(self.mock_gameplay, custom_events)
        self.mock_gameplay.subscribe_to_events.assert_called_once_with(
            custom_events, self.mock_event_aggregator
        )

    def test_listen_handles_edge_cases(self):
        """Test listen method with unexpected inputs."""

        # Missing payload
        with self.assertRaises(TypeError):
            self.dispatcher.listen(None, GameEventType.FINISH)
