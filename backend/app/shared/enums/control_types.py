from __future__ import annotations

from enum import StrEnum


class Controls(StrEnum):
    """Enumeration of all possible game control types."""

    # Game Controls
    GAME_CONTROL_START = "game.control.start"
    GAME_CONTROL_PAUSE = "game.control.pause"
    GAME_CONTROL_RESUME = "game.control.resume"
    GAME_CONTROL_SPEED = "game.control.speed"
