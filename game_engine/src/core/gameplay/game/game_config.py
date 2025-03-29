from src.core.models import Team, Set
from src.core.rules import RuleEvaluator
from game_engine.src.core.gameplay.game.match_type import MatchType


class GameConfig:
    def __init__(self, game_id, rule_eval, team1, team2, match_type=None, set=None):
        self.game_id: str = game_id
        self.rule_eval: RuleEvaluator = rule_eval
        self.match_type: MatchType = match_type
        self.team1: Team = team1
        self.team2: Team = team2
        self.set_manager: Set = set or Set()
