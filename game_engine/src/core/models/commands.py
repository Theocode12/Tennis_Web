from src.core.gameplay import GamePlay
from abc import ABC, abstractmethod


class GameCommand(ABC):
    def __init__(self, id):
        self.gameid = id

    @abstractmethod
    def execute(self, gameplay: GamePlay):
        pass


class StartGameCommand(GameCommand):
    def execute(self, gameplay: GamePlay):
        gameplay.start()


class PauseGameCommand(GameCommand):
    def execute(self, gameplay: GamePlay):
        gameplay.pause()


class ResumeGameCommand(GameCommand):
    def execute(self, gameplay: GamePlay):
        gameplay.resume()


class StopGameCommand(GameCommand):
    def execute(self, gameplay: GamePlay):
        gameplay.stop()
