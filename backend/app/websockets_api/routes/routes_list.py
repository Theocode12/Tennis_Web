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
from app.shared.enums.message_types import MessageType

ROUTE_LIST: list[tuple[MessageType, type[BaseHandler], type[BaseModel] | None]] = [
    (MessageType.GAME_CONTROL_START, StartControlHandler, GameControlSchema),
    (MessageType.GAME_CONTROL_PAUSE, PauseControlHandler, GameControlSchema),
    (MessageType.GAME_CONTROL_RESUME, ResumeControlHandler, GameControlSchema),
    (MessageType.GAME_CONTROL_SPEED, SpeedControlHandler, SpeedControlSchema),
    (MessageType.GAME_JOIN, JoinGameHandler, JoinGameSchema),
]
