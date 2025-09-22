from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from app.handlers.base import BaseHandler
from app.shared.enums.game_event import GameEvent
from app.websockets_api.routes.router import Router


# --- Test Fixtures and Mocks ---
class DummyHandler(BaseHandler):
    async def handle(self, sid: str, data: dict[str, Any]) -> None:
        pass


class AnotherDummyHandler(BaseHandler):
    async def handle(self, sid: str, data: dict[str, Any]) -> None:
        pass


class DummySchema(BaseModel):
    field: str


@pytest.fixture
def mock_logger() -> MagicMock:
    """Provides a mocked logger instance."""
    return MagicMock()


@pytest.fixture
def router(mock_logger: MagicMock) -> Router:
    """Provides a Router instance with a mocked logger."""
    return Router(logger=mock_logger)


# --- Test Cases ---


def test_router_initialization(router: Router) -> None:
    """Test that the Router initializes with an empty routes dictionary."""
    assert router.routes == {}


def test_register_route_success(router: Router) -> None:
    """Test that a new route is correctly registered."""
    event = GameEvent.GAME_JOIN
    router.register_route(event, DummyHandler, DummySchema)

    assert event in router.routes
    definition = router.routes[event]
    assert definition["handler"] is DummyHandler
    assert definition["schema"] is DummySchema


def test_register_route_overwrite_logs_warning(
    router: Router, mock_logger: MagicMock
) -> None:
    """Test that overwriting an existing route logs a warning."""
    event = GameEvent.GAME_JOIN

    # First registration
    router.register_route(event, DummyHandler, DummySchema)
    mock_logger.warning.assert_not_called()

    # Overwrite registration
    router.register_route(event, AnotherDummyHandler, None)

    # Assert warning was logged and route was updated
    mock_logger.warning.assert_called_once()
    assert "Overwriting route" in mock_logger.warning.call_args[0][0]
    assert router.routes[event]["handler"] is AnotherDummyHandler


def test_get_definition_success(router: Router) -> None:
    """Test retrieving a definition for a registered route."""
    event = GameEvent.GAME_JOIN
    router.register_route(event, DummyHandler, DummySchema)

    definition = router.get_definition(event)

    assert definition is not None
    assert definition["handler"] is DummyHandler
    assert definition["schema"] is DummySchema


def test_get_definition_not_found(router: Router, mock_logger: MagicMock) -> None:
    """Test that getting a non-existent route returns None and logs a warning."""
    definition = router.get_definition(GameEvent.GAME_JOIN)

    assert definition is None
    mock_logger.warning.assert_called_once()
    assert "No route found" in mock_logger.warning.call_args[0][0]


def test_load_routes(router: Router) -> None:
    """Test that `load_routes` registers all routes from the ROUTE_LIST."""
    mock_route_list = [
        (GameEvent.GAME_JOIN, DummyHandler, DummySchema),
        (GameEvent.GAME_CONTROL_START, AnotherDummyHandler, None),
    ]

    with patch(
        "app.websockets_api.routes.routes_list.ROUTE_LIST",
        mock_route_list,
        create=True,
    ):
        router.load_routes()

    assert len(router.routes) == 2

    # Verify first route
    join_def = router.get_definition(GameEvent.GAME_JOIN)
    assert join_def is not None
    assert join_def["handler"] is DummyHandler
    assert join_def["schema"] is DummySchema

    # Verify second route
    start_def = router.get_definition(GameEvent.GAME_CONTROL_START)
    assert start_def is not None
    assert start_def["handler"] is AnotherDummyHandler
    assert start_def["schema"] is None
