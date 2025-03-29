from typing import Optional
from src.core.constants import TennisConstantsBase


class GameRule:
    def __init__(self, constant: TennisConstantsBase, tie_break_rule=None):
        self.min_points = constant.MIN_POINTS_TO_WIN_GAME
        self.min_diff = constant.MIN_POINTS_DIFFERENCE_TO_WIN_GAME
        self.tie_break_rule = tie_break_rule or TieBreakRule(constant)

    def has_team_won_game(
        self,
        team_points: int,
        opponent_points: int,
        is_tiebreak=False,
    ) -> bool:
        if is_tiebreak:
            return self.tie_break_rule.has_team_won_tie_break(
                team_points, opponent_points
            )
        return (
            team_points >= self.min_points
            and (team_points - opponent_points) >= self.min_diff
        )


class SetRule:
    def __init__(self, constant: TennisConstantsBase, tie_break_rule=None):
        self.min_set_points = constant.MIN_SET_POINTS
        self.min_set_diff = constant.MIN_SET_DIFFERENCE
        self.max_set_points = constant.MAX_SET_POINTS
        self.tie_break_rule = tie_break_rule or TieBreakRule(constant)

    def has_team_won_set(
        self,
        team_set_points: int,
        opponent_set_points: int,
    ) -> bool:

        # if is_tiebreak:
        #     if not isinstance(team_points, int) or not isinstance(opponent_points, int):
        #         raise Exception("team points or opposition points must be an Int")
        #     return self.tie_break_rule.has_team_won_tie_break(
        #         team_points, opponent_points
        #     )

        # either you at the max return true
        # or diff btw two team must >= set_diff
        return (team_set_points == self.max_set_points) or (
            team_set_points >= self.min_set_points
            and (team_set_points - opponent_set_points) >= self.min_set_diff
        )


class MatchRule:
    def __init__(self, constant: TennisConstantsBase):
        self.max_sets = constant.SETS_TO_WIN_MATCH

    def has_team_won_match(self, team_sets_won: int) -> bool:
        return team_sets_won >= self.max_sets


class TieBreakRule:
    def __init__(self, constant: TennisConstantsBase):
        self.tiebreak_trigger_score = constant.TIEBREAK_TRIGGER_SCORE
        self.min_tiebreak_diff = constant.MIN_TIEBREAK_POINT_DIFFERENCE
        self.min_tiebreak_points = constant.MIN_TIEBREAK_POINTS

    def is_tiebreak(self, team_set_points: int, opponent_set_points: int) -> bool:
        return (
            team_set_points == self.tiebreak_trigger_score
            and opponent_set_points == self.tiebreak_trigger_score
        )

    def has_team_won_tie_break(self, team_points: int, opponent_points: int) -> bool:
        return (
            team_points >= self.min_tiebreak_points
            and (team_points - opponent_points) >= self.min_tiebreak_diff
        )
