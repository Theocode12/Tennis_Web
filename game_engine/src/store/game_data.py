from dataclasses import dataclass
from typing import List, Dict
from src.core.models import Team

@dataclass
class PlayerData:
    """Represents a player's essential details."""
    name: str

@dataclass
class TeamData:
    """Represents a team with its name and players."""
    name: str
    players: List[PlayerData]

@dataclass
class GameData:
    """Represents a structured format for storing game-related data."""
    game_id: str
    teams: Dict[str, TeamData]

    @classmethod
    def from_game_play(cls, game_play):
        """Extracts game data from GamePlay object and returns a structured instance."""
        config = game_play.game_logic.config

        def extract_player_data(team: Team):
            return [
                PlayerData(**{field: getattr(player, field, None) for field in player.visible_fields})
                for player in team.players
            ]

        return cls(
            game_id=game_play.game_id,
            teams={
                "team_1": TeamData(name=config.team1.name, players=extract_player_data(config.team1)),
                "team_2": TeamData(name=config.team2.name, players=extract_player_data(config.team2))
            }
        )
