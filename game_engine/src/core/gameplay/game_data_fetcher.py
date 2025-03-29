from src.core.gameplay.game_play import GamePlay
from typing import Dict

# Manages the loaded game from the redis for now a file
class GameDataFetcher:
    def __init__(self):
        pass

    async def generate_game_point(self, gameplay: GamePlay):
        pass

    async def remove_game(self, game_id: str):
        pass

    async def get_game(self, game_id: str) -> GamePlay:
        pass

