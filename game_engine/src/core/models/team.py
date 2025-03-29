from .point import Points
from .player import Player
from typing import List, Optional


class Team:
    def __init__(self, players: Optional[List[Player]] = None, name: str = None):
        self.name = name
        self.players = []
        self.points = Points()
        self.add_players(players)

    def _link_player_to_team(self):
        for player in self.players:
            player.team = self

    @property
    def name(self):
        return self.__name or self.players_name()

    @name.setter
    def name(self, name):
        self.__name = name

    def players_name(self) -> List[str]:
        return [player.name for player in self.players]

    def add_players(self, players: List[Player]):
        if players is None:
            return
        self.players.extend(players)
        self._link_player_to_team()

    def reset_game_points(self):
        """Reset the current game points."""
        self.points.reset()

    def get_game_points(self):
        return self.points.get_curr_pts()

    def __str__(self):
        player_names = ", ".join(player.name for player in self.players)
        return (
            f"Team: [{player_names}], "
            f"Game Points: {self.points.current_points}, "
            f"Total Points: {self.points.total_points}, "
            f"Sets: {self.sets}"
        )
