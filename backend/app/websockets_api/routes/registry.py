"""
ROUTES stores the mapping of message types to handler classes and schemas.
The message types are strings that define the event type, e.g. "game.join", "game.pause".
Each entry in the ROUTES dictionary maps a message type (such as "game.join") to:
  - "handler": The class that will handle the message, e.g., JoinGameHandler
  - "schema": The schema used for validating incoming data for that message type (optional)
"""
from typing import Type, Optional, TypedDict
from backend.app.handlers.base import BaseHandler
from backend.app.shared.enums.message_types import MessageType
from pydantic import BaseModel

class RouteDefinition(TypedDict):
    handler: Type[BaseHandler]
    schema: Optional[Type[BaseModel]]

ROUTES: dict[str, RouteDefinition] = {}

def register_route(
    message_type: MessageType,
    handler: Type[BaseHandler],
    schema: Optional[Type[BaseModel]] = None
):
    """Registers a handler and optional schema for a given message type."""
    if message_type in ROUTES:
        print(f"Warning: Overwriting route for message type '{message_type}'")
    ROUTES[message_type] = {"handler": handler, "schema": schema}

