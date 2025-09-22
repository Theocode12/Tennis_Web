from __future__ import annotations

import logging
from typing import TypedDict

from pydantic import BaseModel

from app.handlers.base import BaseHandler
from app.shared.enums.game_event import GameEvent
from utils.logger import get_logger


class RouteDefinition(TypedDict):
    handler: type[BaseHandler]
    schema: type[BaseModel] | None


class Router:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or get_logger()
        self.routes: dict[str, RouteDefinition] = {}

    def register_route(
        self,
        event_type: GameEvent,
        handler: type[BaseHandler],
        schema: type[BaseModel] | None = None,
    ) -> None:
        if event_type in self.routes:
            self.logger.warning(
                f"Router: Overwriting route for message type '{event_type}'"
            )
        self.routes[event_type] = {"handler": handler, "schema": schema}

    def load_routes(self) -> None:
        from app.websockets_api.routes.routes_list import ROUTE_LIST

        for event_type, handler, schema in ROUTE_LIST:
            self.register_route(event_type, handler, schema)

    def get_definition(self, event_type: GameEvent) -> RouteDefinition | None:
        """Get the route definition for a given event type."""
        if event_type not in self.routes:
            self.logger.warning(
                f"Router: No route found for message type '{event_type}'"
            )
            return None
        return self.routes.get(event_type)
