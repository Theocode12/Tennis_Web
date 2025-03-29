import unittest
from unittest.mock import MagicMock
from src.core.rules import RuleEvaluator, TennisRules


class TestRuleEvaluator(unittest.TestCase):

    def setUp(self):
        # Create a mock TennisRules object
        self.mock_rules = MagicMock(spec=TennisRules)
        self.rule_evaluator = RuleEvaluator(rules=self.mock_rules)

    def test_check_game_winner(self):
        # Arrange
        self.mock_rules.get_game_rule().has_team_won_game.return_value = True
        player_points, opponent_points = 4, 2

        # Act
        result = self.rule_evaluator.check_game_winner(player_points, opponent_points)

        # Assert
        self.assertTrue(result, "Player should win the game")
        self.mock_rules.get_game_rule().has_team_won_game.assert_called_with(
            player_points, opponent_points, False
        )

    def test_check_set_winner(self):
        # Arrange
        self.mock_rules.get_set_rule().has_team_won_set.return_value = True
        player_set_points, opponent_set_points = 6, 4

        # Act
        result = self.rule_evaluator.check_set_winner(
            player_set_points, opponent_set_points
        )

        # Assert
        self.assertTrue(result, "Player should win the set")
        self.mock_rules.get_set_rule().has_team_won_set.assert_called_with(
            player_set_points, opponent_set_points
        )

    def test_check_match_winner(self):
        # Arrange
        player_sets_won = 3
        self.mock_rules.get_match_rule().has_team_won_match.return_value = True

        # Act
        result = self.rule_evaluator.check_match_winner(player_sets_won)

        # Assert
        self.assertTrue(result, "Player should win the match")
        self.mock_rules.get_match_rule().has_team_won_match.assert_called_with(
            player_sets_won
        )

    def test_check_tiebreak(self):
        # Arrange
        player_set_points, opponent_set_points = 6, 6
        self.mock_rules.get_tiebreak_rule().is_tiebreak.return_value = True

        # Act
        result = self.rule_evaluator.check_tiebreak(
            player_set_points, opponent_set_points
        )

        # Assert
        self.assertTrue(result, "Should be a tiebreak")
        self.mock_rules.get_tiebreak_rule().is_tiebreak.assert_called_with(
            player_set_points, opponent_set_points
        )


if __name__ == "__main__":
    unittest.main()
