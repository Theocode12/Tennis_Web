from abc import ABC, abstractmethod
from src.core.rules import MatchRule, GameRule, SetRule, TieBreakRule


class TennisRules(ABC):
    @abstractmethod
    def get_game_rule(self) -> GameRule:
        pass

    @abstractmethod
    def get_set_rule(self) -> SetRule:
        pass

    @abstractmethod
    def get_match_rule(self) -> MatchRule:
        pass

    @abstractmethod
    def get_tiebreak_rule(self) -> TieBreakRule:
        pass
