from __future__ import annotations

from enum import StrEnum

from .control_types import Controls

# This file defines the ClientEvent enumeration, which contains all possible
# events that can be sent to the client.
# It also means that is are all the events a client can listen to.


class ClientEvent(StrEnum):
    """Enumeration of all possible events that can be sent to the client."""

    # Game Events
    GAME_JOIN = "game.join"
    GAME_LEAVE = "game.leave"
    GAME_START = "game.start"
    GAME_END = "game.end"

    # Game Controls
    GAME_CONTROL_START = Controls.GAME_CONTROL_START
    GAME_CONTROL_PAUSE = Controls.GAME_CONTROL_PAUSE
    GAME_CONTROL_RESUME = Controls.GAME_CONTROL_RESUME
    GAME_CONTROL_SPEED = Controls.GAME_CONTROL_SPEED

    # Game Updates
    GAME_SCORE_UPDATE = "game.score.update"

    # Error
    ERROR = "game.error"
