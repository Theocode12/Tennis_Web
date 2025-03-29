import unittest
from unittest.mock import MagicMock
from src.core.models.events import EventAggregator, EventSubscriber


class TestEventAggregator(unittest.TestCase):
    def setUp(self):
        self.aggregator = EventAggregator()
        self.mock_listener = MagicMock(spec=EventSubscriber)

    def test_subscribe_and_dispatch(self):
        self.aggregator.subscribe("123", "test_event", self.mock_listener)
        self.aggregator.dispatch("test_event", {"_id": "123", "key": "value"})
        self.mock_listener.listen.assert_called_once_with(
            {"_id": "123", "key": "value"}, "test_event"
        )

    def test_unsubscribe(self):
        self.aggregator.subscribe("123", "test_event", self.mock_listener)
        self.aggregator.unsubscribe("123", "test_event")
        self.aggregator.dispatch("test_event", {"_id": "123", "key": "value"})
        self.mock_listener.listen.assert_not_called()

    def test_dispatch_no_subscribers(self):
        # No error should occur when no listeners are registered
        self.aggregator.dispatch("nonexistent_event", {"key": "value"})
