import unittest
from src.constants import TennisConstantsBase, CustomTournamentConstants
from src.rules import GameRule, SetRule, MatchRule, TieBreakRule


# class TestGameRule(unittest.TestCase):

#     def setUp(self):
#         self.rule = GameRule(TennisConstantsBase())

#     def test_player_wins_game(self):
#         self.assertTrue(self.rule.has_player_won_game(4, 2))
#         self.assertTrue(self.rule.has_player_won_game(5, 3))
#         self.assertFalse(self.rule.has_player_won_game(3, 2))
#         self.assertFalse(self.rule.has_player_won_game(4, 5))

# class TestSetRule(unittest.TestCase):

#     def setUp(self):
#         self.tie_break_rule = TieBreakRule()
#         self.rule = SetRule(tie_break_rule=self.tie_break_rule)

#     def test_player_wins_set(self):
#         self.assertTrue(self.rule.has_player_won_set(6, 4))
#         self.assertTrue(self.rule.has_player_won_set(7, 5))
#         self.assertFalse(self.rule.has_player_won_set(5, 4))
#         self.assertFalse(self.rule.has_player_won_set(6, 6))

#     def test_player_wins_set_with_tiebreak(self):
#         self.assertTrue(self.rule.has_player_won_set(6, 6, player_points=7, opponent_points=5, is_tiebreak=True))
#         self.assertFalse(self.rule.has_player_won_set(6, 6, player_points=6, opponent_points=4, is_tiebreak=True))


# class TestMatchRule(unittest.TestCase):

#     def setUp(self):
#         self.rule = MatchRule()

#     def test_player_wins_match(self):
#         self.assertTrue(self.rule.has_player_won_match(2))
#         self.assertFalse(self.rule.has_player_won_match(1))


# class TestTieBreakRule(unittest.TestCase):

#     def setUp(self):
#         self.rule = TieBreakRule()

#     def test_is_tiebreak(self):
#         self.assertFalse(self.rule.is_tiebreak(7, 7))
#         self.assertTrue(self.rule.is_tiebreak(6, 6))
#         self.assertFalse(self.rule.is_tiebreak(7, 6))

#     def test_player_wins_tiebreak(self):
#         self.assertTrue(self.rule.has_player_won_tie_break(7, 5))
#         self.assertFalse(self.rule.has_player_won_tie_break(6, 6))
#         self.assertFalse(self.rule.has_player_won_tie_break(7, 6))


class TestGameRule(unittest.TestCase):

    def setUp(self):
        # Using base constants for standard game rule
        self.rule = GameRule(TennisConstantsBase())

    def test_player_wins_game(self):
        self.assertTrue(self.rule.has_player_won_game(4, 2))
        self.assertTrue(self.rule.has_player_won_game(5, 3))
        self.assertFalse(self.rule.has_player_won_game(3, 2))
        self.assertFalse(self.rule.has_player_won_game(4, 5))


class TestSetRule(unittest.TestCase):

    def setUp(self):
        # Standard set rule with tiebreaker using base constants
        base_constants = TennisConstantsBase()
        self.tie_break_rule = TieBreakRule(base_constants)
        self.rule = SetRule(base_constants, tie_break_rule=self.tie_break_rule)

    def test_player_wins_set(self):
        self.assertTrue(self.rule.has_player_won_set(6, 4))
        self.assertTrue(self.rule.has_player_won_set(7, 5))
        self.assertFalse(self.rule.has_player_won_set(5, 4))
        self.assertFalse(self.rule.has_player_won_set(6, 6))

    def test_player_wins_set_with_tiebreak(self):
        self.assertTrue(
            self.rule.has_player_won_set(
                6, 6, player_points=7, opponent_points=5, is_tiebreak=True
            )
        )
        self.assertFalse(
            self.rule.has_player_won_set(
                6, 6, player_points=6, opponent_points=4, is_tiebreak=True
            )
        )
        self.assertFalse(
            self.rule.has_player_won_set(
                6, 6, player_points=7, opponent_points=6, is_tiebreak=True
            )
        )

    def test_player_wins_set_with_custom_values(self):
        # Custom constants specifically for set rules
        custom_constants = CustomTournamentConstants(
            MIN_SET_POINTS=7, MIN_SET_DIFFERENCE=2
        )
        custom_rule = SetRule(custom_constants)
        self.assertTrue(custom_rule.has_player_won_set(7, 5))
        self.assertFalse(custom_rule.has_player_won_set(7, 6))


class TestMatchRule(unittest.TestCase):

    def setUp(self):
        # Standard match rule using base constants
        self.rule = MatchRule(TennisConstantsBase())

    def test_player_wins_match(self):
        self.assertTrue(self.rule.has_player_won_match(2))
        self.assertFalse(self.rule.has_player_won_match(1))

    def test_player_wins_match_with_custom_values(self):
        # Custom constants specifically for match rules
        custom_constants = CustomTournamentConstants(SETS_TO_WIN_MATCH=3)
        custom_rule = MatchRule(custom_constants)
        self.assertTrue(custom_rule.has_player_won_match(3))
        self.assertFalse(custom_rule.has_player_won_match(2))


class TestTieBreakRule(unittest.TestCase):

    def setUp(self):
        # Standard tiebreak rule using base constants
        self.rule = TieBreakRule(TennisConstantsBase())

    def test_is_tiebreak(self):
        self.assertFalse(self.rule.is_tiebreak(7, 7))
        self.assertTrue(self.rule.is_tiebreak(6, 6))
        self.assertFalse(self.rule.is_tiebreak(7, 6))

    def test_player_wins_tiebreak(self):
        self.assertTrue(self.rule.has_player_won_tie_break(7, 5))
        self.assertFalse(self.rule.has_player_won_tie_break(6, 6))
        self.assertFalse(self.rule.has_player_won_tie_break(7, 6))

    def test_player_wins_tiebreak_with_custom_values(self):
        # Custom constants for specific tiebreak rule scenarios
        custom_tie_constants = CustomTournamentConstants(
            MIN_TIEBREAK_POINT_DIFFERENCE=3
        )
        custom_tie_rule = TieBreakRule(custom_tie_constants)
        self.assertTrue(custom_tie_rule.has_player_won_tie_break(7, 4))
        self.assertFalse(custom_tie_rule.has_player_won_tie_break(7, 5))

        custom_tie_constants = CustomTournamentConstants(
            MIN_TIEBREAK_POINTS=12, MIN_TIEBREAK_POINT_DIFFERENCE=3
        )
        custom_tie_rule = TieBreakRule(custom_tie_constants)
        self.assertTrue(custom_tie_rule.has_player_won_tie_break(12, 9))
        self.assertFalse(custom_tie_rule.has_player_won_tie_break(12, 10))


if __name__ == "__main__":
    unittest.main()
