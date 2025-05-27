from __future__ import annotations

import logging
from typing import TypedDict

from pydantic import BaseModel
from utils.logger import get_logger

from app.handlers.base import BaseHandler
from app.shared.enums.message_types import MessageType


class RouteDefinition(TypedDict):
    handler: type[BaseHandler]
    schema: type[BaseModel] | None


class Router:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or get_logger()
        self.routes: dict[str, RouteDefinition] = {}

    def register_route(
        self,
        message_type: MessageType,
        handler: type[BaseHandler],
        schema: type[BaseModel] | None = None,
    ) -> None:
        if message_type in self.routes:
            self.logger.warning(
                f"Router: Overwriting route for message type '{message_type}'"
            )
        self.routes[message_type] = {"handler": handler, "schema": schema}

    def load_routes(self) -> None:
        from app.websockets_api.routes.routes_list import ROUTE_LIST

        for message_type, handler, schema in ROUTE_LIST:
            self.register_route(message_type, handler, schema)

    def get_definition(self, message_type: MessageType) -> RouteDefinition | None:
        """Get the route definition for a given message type."""
        if message_type not in self.routes:
            self.logger.warning(
                f"Router: No route found for message type '{message_type}'"
            )
            return None
        return self.routes.get(message_type)
