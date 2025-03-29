from src.lib.singleton_metaclass import SingletonMeta


# Base Storage Class
class BaseStorage(metaclass=SingletonMeta):
    async def append_score(self, game_id, data):
        raise NotImplementedError
    
    async def store_game_data(self, data):
        raise NotImplementedError
