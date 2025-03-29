from src.core.rules import TennisRules, GameRule, SetRule, MatchRule, TieBreakRule
from src.core.constants import (
    TennisConstantsBase,
    GrandSlamConstants,
    CustomTournamentConstants,
)


class GrandSlamRules(TennisRules):
    def __init__(self):
        self.constants = GrandSlamConstants()
        self.game_rule = GameRule(self.constants)
        self.set_rule = SetRule(self.constants)
        self.match_rule = MatchRule(self.constants)
        self.tiebreak_rule = TieBreakRule(self.constants)

    def get_game_rule(self):
        return self.game_rule

    def get_set_rule(self):
        return self.set_rule

    def get_match_rule(self):
        return self.match_rule

    def get_tiebreak_rule(self):
        return self.tiebreak_rule


class RegularTournamentRules(TennisRules):
    def __init__(self):
        self.constants = TennisConstantsBase()
        self.game_rule = GameRule(self.constants)
        self.set_rule = SetRule(self.constants)
        self.match_rule = MatchRule(self.constants)
        self.tiebreak_rule = TieBreakRule(self.constants)

    def get_game_rule(self):
        return self.game_rule

    def get_set_rule(self):
        return self.set_rule

    def get_match_rule(self):
        return self.match_rule

    def get_tiebreak_rule(self):
        return self.tiebreak_rule


class CustomTennisRules(TennisRules):
    def __init__(self, constant: CustomTournamentConstants):
        self.game_rule = GameRule(constant)
        self.set_rule = SetRule(constant)
        self.match_rule = MatchRule(constant)
        self.tiebreak_rule = TieBreakRule(constant)

    def get_game_rule(self):
        return self.game_rule

    def get_set_rule(self):
        return self.set_rule

    def get_match_rule(self):
        return self.match_rule

    def get_tiebreak_rule(self):
        return self.tiebreak_rule
