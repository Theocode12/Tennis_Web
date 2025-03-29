from src.core.models.events.event_subscriber import EventSubscriber
from src.core.models.events.event_type import EventType
from threading import Lock
from typing import Dict


class EventAggregator:
    def __init__(self):
        self.listeners: Dict[EventType, Dict[str, EventSubscriber]] = {}
        self.lock = Lock()

    def subscribe(self, _id: str, event_type: EventType, listener: EventSubscriber):
        with self.lock:
            if event_type not in self.listeners:
                self.listeners[event_type] = {}
            self.listeners[event_type][_id] = listener

    def unsubscribe(self, _id: str, event_type: EventType):
        with self.lock:
            if event_type in self.listeners:
                self.listeners[event_type].pop(_id, None)

    def dispatch(self, event_type, payload):
        with self.lock:
            _id = payload.get("_id")
            if event_type in self.listeners:
                if _id in self.listeners[event_type]:
                    self.listeners[event_type][_id].listen(payload, event_type)
                else:
                    print(f"No listener for game_id {_id} and event {event_type}")
