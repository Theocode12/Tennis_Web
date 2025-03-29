from src.core.gameplay.game.game_logic import GameLogic


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

    def run(self):
        try:
            while not self.game_logic.is_game_over():
                self.game_logic.execute()
        except Exception as e:
            print(f"Error in Game {self.game_id}: {e}")
        finally:
            print(f"Game {self.game_id} exiting.")
