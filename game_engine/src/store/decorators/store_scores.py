from src.store.base_storage import BaseStorage
from functools import wraps

# Decorator for Storing Results
def store_scores(storage: BaseStorage):
    def decorator(func):
        @wraps(func)
        async def wrapper(game_logic, *args, **kwargs):
            result = await func(game_logic, *args, **kwargs)  # Run the original method
            game_id = game_logic.config.game_id
            score_payload = game_logic.generate_score_payload()
            await storage.append_score(game_id, score_payload)
            return result
        return wrapper
    return decorator
