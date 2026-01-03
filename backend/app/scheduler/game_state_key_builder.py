class GameStateKeyBuilder:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix.rstrip(":")

    def key(self, game_id: str) -> str:
        return f"{self.prefix}:{game_id}"
