import random
from src.core.models import Team, Player
from typing import List


class PointAllocator:
    def __init__(self):
        self.teams = None

    def set_teams(self, teams: List[Team]):
        if len(teams) != 2:
            raise ValueError("Wrong number of teams")
        self.teams = teams

    def allocate_point(self):
        """Randomly assigns a point to a player from one of the teams."""
        team: Team = random.choice(self.teams)  # Pick a random team
        player: Player = random.choice(team.players)  # Pick a random player in the team
        return player.win_point()
