from src.store.base_storage import BaseStorage
from functools import wraps

# Decorator for Storing Results
def store_results(storage: BaseStorage):
    def decorator(func):
        @wraps(func)
        async def wrapper(game_logic, *args, **kwargs):
            result = func(game_logic, *args, **kwargs)  # Run the original method
            game_id = game_logic.config.game_id
            score_payload = game_logic.generate_score_payload()
            await storage.save_result(game_id, score_payload)
            return result
        return wrapper
    return decorator