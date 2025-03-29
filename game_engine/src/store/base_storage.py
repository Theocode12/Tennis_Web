from src.lib.singleton_metaclass import SingletonMeta


# Base Storage Class
class BaseStorage(metaclass=SingletonMeta):
    async def save_result(self, game_id, data):
        raise NotImplementedError
