from . import BasePlayerView


class ScoreboardTeamView(BasePlayerView):
    def __init__(self, name: str, game_points: int, set_points: list):
        super().__init__(name)
        self.game_points = game_points
        self.set_points = set_points

    def __eq__(self, other):
        if not isinstance(other, ScoreboardTeamView):
            return False
        return (
            self.name == other.name
            and self.game_points == other.game_points
            and self.set_points == other.set_points
        )
