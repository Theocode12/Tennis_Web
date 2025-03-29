from src.core.models.events import EventSubscriber
from ..displays import Display
from abc import abstractmethod


class Board(EventSubscriber):

    @abstractmethod
    def get_view(self):
        pass

    @abstractmethod
    def register_display(self, display: Display):
        pass

    @abstractmethod
    def remove_display(self, display: Display):
        pass

    @abstractmethod
    def notify_display(self):
        pass
