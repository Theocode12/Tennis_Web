from abc import ABC, abstractmethod


class EventSubscriber(ABC):
    @abstractmethod
    def listen(self, payload, event):
        pass
