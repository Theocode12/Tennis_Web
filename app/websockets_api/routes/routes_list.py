from __future__ import annotations

from pydantic import BaseModel

from app.handlers.base import BaseHandler
from app.handlers.game_controls import (
    GameControlSchema,
    PauseControlHandler,
    ResumeControlHandler,
    SpeedControlHandler,
    SpeedControlSchema,
    StartControlHandler,
)
from app.handlers.join_game import JoinGameHandler, JoinGameSchema
from app.shared.enums.game_event import GameEvent

ROUTE_LIST: list[tuple[GameEvent, type[BaseHandler], type[BaseModel] | None]] = [
    (GameEvent.GAME_CONTROL_START, StartControlHandler, GameControlSchema),
    (GameEvent.GAME_CONTROL_PAUSE, PauseControlHandler, GameControlSchema),
    (GameEvent.GAME_CONTROL_RESUME, ResumeControlHandler, GameControlSchema),
    (GameEvent.GAME_CONTROL_SPEED, SpeedControlHandler, SpeedControlSchema),
    (GameEvent.GAME_JOIN, JoinGameHandler, JoinGameSchema),
]
