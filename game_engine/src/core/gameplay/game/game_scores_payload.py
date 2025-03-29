from src.core.models import Set, Team


class ScorePayload:
    def __init__(self, team1: Team, team2: Team, set_obj: Set):
        self.team1 = team1
        self.team2 = team2
        self.set_obj = set_obj

    def to_dict(self):
        return {
            "set": self.set_obj.transform_set_data(),
            "game_points": [self.team1.get_game_points(), self.team2.get_game_points()]
        }
