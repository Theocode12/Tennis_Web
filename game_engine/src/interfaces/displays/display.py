from abc import ABC, abstractmethod


class Display(ABC):

    @abstractmethod
    def render(self):
        pass
