# Redis Storage Singleton
from .base_storage import BaseStorage

# File Storage Singleton
class FileStorage(BaseStorage):
    def __init__(self, directory):
        self.directory = directory

    async def save_result(self, game_id, data):
        with open(f"{self.directory}/{game_id}.json", "w") as file:
            file.write(data)