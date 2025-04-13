from pathlib import Path


class BackendFileStorage:
    """File-based storage for backend operations"""
    
    def __init__(self, base_path: str = "./data/games", file_extension: str = ".json"):
        self.base_path = Path(base_path)
        self.file_extension = file_extension
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_game_path(self, game_id: str) -> Path:
        """Get path for game-specific directory"""
        game_path = self.base_path.joinpath(f"{game_id}{self.file_extension}")
        return game_path
