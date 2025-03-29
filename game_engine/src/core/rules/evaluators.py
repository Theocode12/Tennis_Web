from src.core.rules import TennisRules


class RuleEvaluator:
    def __init__(self, rules: TennisRules):
        self.rules = rules

    def check_game_winner(self, player_points, opponent_points, is_tiebreak=False):
        return self.rules.get_game_rule().has_team_won_game(
            player_points, opponent_points, is_tiebreak
        )

    def check_set_winner(
        self,
        player_set_points,
        opponent_set_points,
    ):
        return self.rules.get_set_rule().has_team_won_set(
            player_set_points,
            opponent_set_points,
        )

    def check_match_winner(self, player_sets_won):
        return self.rules.get_match_rule().has_team_won_match(player_sets_won)

    def check_tiebreak(self, player_set_points, opponent_set_points):
        return self.rules.get_tiebreak_rule().is_tiebreak(
            player_set_points, opponent_set_points
        )
