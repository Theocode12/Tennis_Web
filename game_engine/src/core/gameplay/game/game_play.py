from src.core.gameplay.game.game_logic import GameLogic
from src.store.decorators.store_game_data import store_game_data
from src.store.file_storage import FileStorage

class GamePlay:
    def __init__(
        self,
        game_id,
        name,
        game_logic,
    ) -> None:
        self.game_id: str = game_id
        self.name: str = name
        self.game_logic: GameLogic = game_logic

    @store_game_data(FileStorage('games'))
    async def run(self):
        try:
            while not self.game_logic.is_game_over():
                await self.game_logic.execute()
        except Exception as e:
            raise e
            print(f"Error in Game {self.game_id}: {e}")
        finally:
            print(f"Game {self.game_id} exiting.")
