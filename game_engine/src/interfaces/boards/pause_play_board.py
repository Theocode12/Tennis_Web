from .board import Board
from src.interfaces.displays import Display
from typing import Optional, List


class PausePlayBoard(Board):
    def __init__(self, *displays: Optional[List[Display]]) -> None:
        self._displays: List[Display] = [*displays]

    @property
    def displays(self):
        return self._displays

    @displays.setter
    def displays(self, displays: List[Display]):
        self._displays = displays

    def register_display(self, display: Display):
        self._displays.append(display)

    def remove_display(self, display: Display):
        self._displays.remove(display)

    def notify_display(self):
        for display in self._displays:
            display.render()
