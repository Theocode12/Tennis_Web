from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.handlers.auth_base import AuthenticatedHandler
from app.shared.enums.broker_channels import BrokerChannels
from app.shared.enums.client_events import ClientEvent
from app.shared.enums.message_types import MessageType


class GameControlHandler(AuthenticatedHandler):
    """
    Base handler for authenticated game control messages.

    Publishes control commands (start, pause, resume, speed, etc.)
    to the game's control broker channel.
    """

    async def handle_authenticated(self, sid: str, data: dict[str, Any]) -> None:
        namespace = data.get("namespace", "")
        game_id = data["game_id"]
        if not self.context.scheduler_manager.has_scheduler(game_id):
            await self.context.sio.emit(
                ClientEvent.ERROR,
                {"error": "Game not found or not running"},
                room=sid,
                namespace=namespace,
            )

        await self.context.broker.publish(game_id, BrokerChannels.CONTROLS, data)


class StartControlHandler(GameControlHandler):
    """
    Handles the 'start game' control event.
    """

    async def handle_authenticated(self, sid: str, data: dict[str, Any]) -> None:
        """
        Publishes a 'start game' control message to the broker.
        """
        return await super().handle_authenticated(sid, data)


class PauseControlHandler(GameControlHandler):
    """
    Handles the 'pause game' control event.
    """

    async def handle_authenticated(self, sid: str, data: dict[str, Any]) -> None:
        """
        Publishes a 'pause game' control message to the broker.
        """
        return await super().handle_authenticated(sid, data)


class ResumeControlHandler(GameControlHandler):
    """
    Handles the 'resume game' control event.
    """

    async def handle_authenticated(self, sid: str, data: dict[str, Any]) -> None:
        """
        Publishes a 'resume game' control message to the broker.
        """
        return await super().handle_authenticated(sid, data)


class SpeedControlHandler(GameControlHandler):
    """
    Handles the 'set game speed' control event.
    """

    async def handle_authenticated(self, sid: str, data: dict[str, Any]) -> None:
        """
        Publishes a 'set speed' control message to the broker.
        """
        return await super().handle_authenticated(sid, data)


class GameControlSchema(BaseModel):
    """
    Schema for standard game control messages (start, pause, resume).
    """

    game_id: str
    token: str
    type: Literal[
        MessageType.GAME_CONTROL_START,
        MessageType.GAME_CONTROL_PAUSE,
        MessageType.GAME_CONTROL_RESUME,
    ]


class SpeedControlSchema(BaseModel):
    """
    Schema for game speed control messages.
    """

    game_id: str
    token: str
    speed: int = Field(..., ge=1, le=7)
    type: Literal[MessageType.GAME_CONTROL_SPEED]
