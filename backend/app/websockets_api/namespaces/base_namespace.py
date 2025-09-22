from __future__ import annotations

from typing import TYPE_CHECKING, Any

from socketio import AsyncNamespace

from app.exceptions.message_error import MessageError
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

    async def on_message(self, sid: str, data: Any) -> None:
        self.logger.debug(
            f"Received 'message' event on {self.namespace} from SID {sid}: {data}"
        )
        try:
            if not isinstance(data, dict):
                raise MessageError("Data must be of type dict.")
            await self.dispatcher.dispatch(sid, data, self.namespace)
        except MessageError as e:
            self.logger.error(f"MessageError in {self.namespace} for SID {sid}: {e}")
            await self.emit(GameEvent.ERROR.value, {"error": str(e)}, to=sid)
        except Exception as e:
            self.logger.exception(
                f"Error processing message in {self.namespace} for SID {sid}: {e}"
            )
            await self.emit(
                GameEvent.ERROR.value,
                {"error": "Internal server error"},
                to=sid,
            )
