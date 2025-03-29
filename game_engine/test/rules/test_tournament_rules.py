import unittest
from unittest.mock import MagicMock
from src.rules import (
    GrandSlamRules,
    RegularTournamentRules,
    CustomTennisRules,
    GameRule,
    MatchRule,
    TieBreakRule,
    SetRule,
)


class TestGrandSlamRules(unittest.TestCase):
    def setUp(self):
        self.rules = GrandSlamRules()

    def test_initialization(self):
        self.assertIsNotNone(self.rules.get_game_rule())
        self.assertIsNotNone(self.rules.get_set_rule())
        self.assertIsNotNone(self.rules.get_match_rule())
        self.assertIsNotNone(self.rules.get_tiebreak_rule())


class TestRegularTournamentRules(unittest.TestCase):
    def setUp(self):
        self.rules = RegularTournamentRules()

    def test_initialization(self):
        self.assertIsNotNone(self.rules.get_game_rule())
        self.assertIsNotNone(self.rules.get_set_rule())
        self.assertIsNotNone(self.rules.get_match_rule())
        self.assertIsNotNone(self.rules.get_tiebreak_rule())


class TestCustomTennisRules(unittest.TestCase):
    def setUp(self):
        self.custom_constants = MagicMock()
        self.rules = CustomTennisRules(self.custom_constants)

    def test_initialization(self):
        self.assertIsInstance(self.rules.get_game_rule(), GameRule)
        self.assertIsInstance(self.rules.get_set_rule(), SetRule)
        self.assertIsInstance(self.rules.get_match_rule(), MatchRule)
        self.assertIsInstance(self.rules.get_tiebreak_rule(), TieBreakRule)
