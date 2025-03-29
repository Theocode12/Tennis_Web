import unittest
from unittest.mock import MagicMock
from src.core.models.events.event_aggregator import EventAggregator
from src.core.models.events.game import GameEventType, GameEventPayload
from src.core.gameplay.game.game_state import GameState
from src.core.gameplay.game.game_event import GameEventManager


class TestGameEventManager(unittest.TestCase):
    def setUp(self):
        # Mocks for EventAggregator and GameState
        self.local_aggregator = MagicMock(spec=EventAggregator)
        self.global_aggregator = MagicMock(spec=EventAggregator)
        self.game_state = MagicMock(spec=GameState)

        # Initialize GameEventManager
        self.game_id = "test_game_id"
        self.manager = GameEventManager(
            game_id=self.game_id,
            game_state=self.game_state,
            local_aggregator=self.local_aggregator,
            global_aggregator=self.global_aggregator,
        )

    def test_subscribe_to_global_events(self):
        events = [GameEventType.START, GameEventType.STOP]
        self.manager.subscribe_to_global_events(events)

        # Check if events were added and subscribed
        self.assertEqual(self.manager.events, events)
        for event in events:
            self.global_aggregator.subscribe.assert_any_call(
                self.game_id, event, self.manager
            )

    def test_unsubscribe_from_global_events(self):
        events = [GameEventType.START, GameEventType.STOP]
        self.manager.subscribe_to_global_events(events)
        self.manager.unsubscribe_from_global_events(events)

        # Check if unsubscribe was called for each event
        for event in events:
            self.global_aggregator.unsubscribe.assert_any_call(self.game_id, event)

    def test_cleanup(self):
        events = [GameEventType.START, GameEventType.STOP]
        self.manager.subscribe_to_global_events(events)
        self.manager.cleanup()

        # Verify unsubscribe is called for all tracked events
        for event in events:
            self.global_aggregator.unsubscribe.assert_any_call(self.game_id, event)

    def test_dispatch_local(self):
        event_type = GameEventType.START
        payload = {"key": "value"}

        self.manager.dispatch_local(event_type, payload)
        self.local_aggregator.dispatch.assert_called_once_with(event_type, payload)

    def test_dispatch_global(self):
        event_type = GameEventType.STOP
        payload = {"key": "value"}

        self.manager.dispatch_global(event_type, payload)
        self.global_aggregator.dispatch.assert_called_once_with(event_type, payload)

    def test_handle_error(self):
        error_message = "An error occurred"
        error_payload = GameEventPayload(
            _id=self.game_id, data={"error": error_message}
        )

        self.manager.handle_error(error_message, error_payload)

        self.global_aggregator.dispatch.assert_called_once_with(
            GameEventType.ERROR, error_payload
        )

    def test_listen_start(self):
        payload = {"key": "value"}
        self.manager.listen(payload, GameEventType.START)

        self.game_state.start.assert_called_once_with(payload)

    def test_listen_stop(self):
        payload = {"key": "value"}
        self.manager.listen(payload, GameEventType.STOP)

        self.game_state.stop.assert_called_once_with(payload)

    def test_listen_pause(self):
        payload = {"key": "value"}
        self.manager.listen(payload, GameEventType.PAUSE)

        self.game_state.pause.assert_called_once_with(payload)

    def test_listen_resume(self):
        payload = {"key": "value"}
        self.manager.listen(payload, GameEventType.RESUME)

        self.game_state.resume.assert_called_once_with(payload)


if __name__ == "__main__":
    unittest.main()
