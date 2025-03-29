from src.core.models import Set, Team
from src.interfaces.displays import Display
from .board import Board
from .views import ScoreboardTeamView, MatchViewData
from typing import Optional, List


class ScoreBoard(Board):
    def __init__(self, *displays: Optional[List[Display]]) -> None:
        self._displays: List[Display] = [*displays]

    @property
    def displays(self):
        return self._displays

    @displays.setter
    def displays(self, displays: List[Display]):
        self._displays = displays

    def register_display(self, display: Display):
        self._displays.append(display)

    def remove_display(self, display: Display):
        self._displays.remove(display)

    def notify_display(self, team_1: Team, team_2: Team, set_obj: Set):
        for display in self._displays:
            display.render(self.get_view(team_1, team_2, set_obj))

    def get_view(self, team_1: Team, team_2: Team, set_obj: Set) -> MatchViewData:
        team1_scores, team2_scores = set_obj.transform_set_data()
        player1_view = ScoreboardTeamView(
            name=team_1.players_name(),
            game_points=team_1.get_game_points(),
            set_points=team1_scores,
        )
        player2_view = ScoreboardTeamView(
            name=team_2.players_name(),
            game_points=team_2.get_game_points(),
            set_points=team2_scores,
        )

        return MatchViewData(player1_view, player2_view)

    def listen(self, payload, event):
        pass  # notify display
