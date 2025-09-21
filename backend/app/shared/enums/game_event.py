from __future__ import annotations

from enum import StrEnum, unique


@unique
class GameEvent(StrEnum):
    """All canonical event strings."""

    # Game
    GAME_JOIN = "game.join"
    GAME_LEAVE = "game.leave"
    GAME_START = "game.start"
    GAME_END = "game.end"

    # Game Controls
    GAME_CONTROL_START = "game.control.start"
    GAME_CONTROL_PAUSE = "game.control.pause"
    GAME_CONTROL_RESUME = "game.control.resume"
    GAME_CONTROL_SPEED = "game.control.speed"

    # Game Updates
    GAME_SCORE_UPDATE = "game.score.update"

    # Error
    ERROR = "game.error"
