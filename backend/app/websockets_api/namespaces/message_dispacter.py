from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from app.exceptions.message_error import MessageError
from app.shared.enums.game_event import GameEvent

if TYPE_CHECKING:
    from app.core.context import AppContext


class MessageDispatcher:
    def __init__(self, context: AppContext):
        self.context = context

    async def dispatch(self, sid: str, data: dict[str, Any], namespace: str) -> None:
        router = self.context.router
        raw_type = data.get("type")

        if not raw_type:
            raise MessageError("event type missing.")

        try:
            event_type = GameEvent(raw_type)
        except ValueError as err:
            raise MessageError(f"Unknown event type: {raw_type}") from err

        route = router.get_definition(event_type)
        if not route:
            raise MessageError(f"Unknown event type: {event_type}")

        schema_cls = route.get("schema")

        try:
            validated_data = (
                data if schema_cls is None else schema_cls(**data).model_dump()
            )
        except ValidationError as e:
            raise MessageError("Invalid data schema.") from e

        handler_cls = route["handler"]
        handler = handler_cls(self.context)
        validated_data.update({"namespace": namespace})
        await handler.handle(sid, validated_data)
