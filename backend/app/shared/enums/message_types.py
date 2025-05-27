from __future__ import annotations

from enum import StrEnum

from .control_types import Controls


class MessageType(StrEnum):
    """Enumeration of all possible websocket message types."""

    # Game Joining
    GAME_JOIN = "game.join"

    # Game Controls
    GAME_CONTROL_START = Controls.GAME_CONTROL_START
    GAME_CONTROL_PAUSE = Controls.GAME_CONTROL_PAUSE
    GAME_CONTROL_RESUME = Controls.GAME_CONTROL_RESUME
    GAME_CONTROL_SPEED = Controls.GAME_CONTROL_SPEED
