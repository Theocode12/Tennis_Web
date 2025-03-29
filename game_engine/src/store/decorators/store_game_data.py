from src.store.base_storage import BaseStorage
from src.store.game_data import GameData
from functools import wraps

# Decorator for Storing Game data such as player data etc
def store_game_data(storage: BaseStorage):
    def decorator(func):
        @wraps(func)
        async def wrapper(game_play, *args, **kwargs):
            # Create a structured GameData object
            game_data = GameData.from_game_play(game_play)
            
            # Convert to dictionary and store
            await storage.store_game_data(game_data)
            result = await func(game_play, *args, **kwargs)
            return result
        return wrapper
    return decorator