import json
import os
from .base_storage import BaseStorage
from src.store.game_data import GameData
from dataclasses import asdict


class FileStorage(BaseStorage):
    def __init__(self, directory: str):
        self.directory = directory
        print(self.directory)
        os.makedirs(directory, exist_ok=True)  # Ensure the directory exists

    def get_file_path(self, game_id: str) -> str:
        """Returns the file path for a given game_id"""
        return os.path.join(self.directory, f"{game_id}.json")

    async def store_game_data(self, data: GameData):
        """Stores game metadata in a JSON file"""
        file_path = self.get_file_path(data.game_id)

        with open(file_path, "w") as file:
            json.dump(asdict(data), file, indent=4)

    async def append_score(self, game_id, score_data):
        """Appends score data to the 'scores' list inside the game file"""
        file_path = self.get_file_path(game_id)

        # Load existing game data
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                game_data = json.load(file)
        else:
            game_data = {"teams": {}, "scores": []}  # Default structure

        # Append new score
        if game_data.get('scores'):
            game_data["scores"].append(score_data)
        else:
            game_data["scores"] = [score_data]
        # Write back to file
        with open(file_path, "w") as file:
            json.dump(game_data, file, indent=4)
