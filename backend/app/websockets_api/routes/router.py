from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel

from app.handlers.base import BaseHandler
from app.shared.enums.message_types import MessageType


class RouteDefinition(TypedDict):
    handler: type[BaseHandler]
    schema: type[BaseModel] | None


class Router:
    def __init__(self) -> None:
        self.routes: dict[str, RouteDefinition] = {}

    def register_route(
        self,
        message_type: MessageType,
        handler: type[BaseHandler],
        schema: type[BaseModel] | None = None,
    ) -> None:
        if message_type in self.routes:
            print(f"Warning: Overwriting route for message type '{message_type}'")
            self.routes[message_type] = {"handler": handler, "schema": schema}

    def load_routes(self) -> None:
        from app.websockets_api.routes.routes_list import ROUTE_LIST

        for message_type, handler, schema in ROUTE_LIST:
            self.register_route(message_type, handler, schema)

    def get_definition(self, message_type: MessageType) -> RouteDefinition | None:
        return self.routes.get(message_type)
