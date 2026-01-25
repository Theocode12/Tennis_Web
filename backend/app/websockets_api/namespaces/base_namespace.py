from __future__ import annotations

from typing import TYPE_CHECKING

from socketio import AsyncNamespace

from app.shared.enums.game_event import GameEvent

from .message_dispacter import MessageDispatcher

if TYPE_CHECKING:
    from app.core.context import AppContext


class BaseNamespace(AsyncNamespace):  # type: ignore[misc]
    def __init__(self, namespace: str, context: AppContext):
        super().__init__(namespace)
        self.context = context
        self.dispatcher = MessageDispatcher(context)
        self.logger = context.logger
        self.logger.info(f"GameNamespace initialized for '{namespace}' namespace.")

    async def emit_error(self, sid: str, message: str) -> None:
        """
        Emit a standardized error event to a single client.
        """
        await self.emit(
            GameEvent.ERROR.value,
            {"error": message},
            to=sid,
        )
