from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.handlers.game_controls import GameControlHandler
from app.shared.enums.broker_channels import BrokerChannels
from app.shared.enums.game_event import GameEvent


@pytest.fixture
def mock_context() -> MagicMock:
    """Provides a mock AppContext for handler tests."""
    context = MagicMock()
    context.auth = MagicMock()
    context.scheduler_manager = MagicMock()
    context.sio = AsyncMock()
    context.broker = AsyncMock()
    context.logger = MagicMock()
    return context


@pytest.fixture
def game_control_handler(mock_context: MagicMock) -> GameControlHandler:
    """Provides a GameControlHandler instance with a mocked context."""
    return GameControlHandler(mock_context)


@pytest.mark.asyncio
async def test_handle_unauthenticated_request(
    game_control_handler: GameControlHandler, mock_context: MagicMock
) -> None:
    """Verify that an unauthenticated request is rejected."""
    # Arrange
    mock_context.auth.validate.return_value = False
    sid = "test_sid"
    data = {"token": "invalid_token", "game_id": "game1", "namespace": "/game"}

    # Act
    await game_control_handler.handle(sid, data)

    # Assert
    mock_context.auth.validate.assert_called_once_with("invalid_token")
    mock_context.sio.emit.assert_awaited_once_with(
        GameEvent.ERROR, {"error": "Unauthorized"}, to=sid
    )
    mock_context.broker.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_game_not_found(
    game_control_handler: GameControlHandler, mock_context: MagicMock
) -> None:
    """Verify that a request for a non-existent game is rejected."""
    # Arrange
    mock_context.auth.validate.return_value = True
    mock_context.scheduler_manager.has_scheduler.return_value = False
    sid = "test_sid"
    game_id = "non_existent_game"
    namespace = "/game"
    data = {"token": "valid_token", "game_id": game_id, "namespace": namespace}

    # Act
    await game_control_handler.handle(sid, data)

    # Assert
    mock_context.auth.validate.assert_called_once_with("valid_token")
    mock_context.scheduler_manager.has_scheduler.assert_called_once_with(game_id)
    mock_context.sio.emit.assert_awaited_once_with(
        GameEvent.ERROR,
        {"error": "Game not found or not running"},
        to=sid,
        namespace=namespace,
    )
    mock_context.broker.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_success_publishes_control_message(
    game_control_handler: GameControlHandler, mock_context: MagicMock
) -> None:
    """Verify a valid request publishes a message to the broker."""
    # Arrange
    mock_context.auth.validate.return_value = True
    mock_context.scheduler_manager.has_scheduler.return_value = True
    sid = "test_sid"
    game_id = "active_game"
    namespace = "/game"
    data = {
        "token": "valid_token",
        "game_id": game_id,
        "type": GameEvent.GAME_CONTROL_PAUSE,
        "namespace": namespace,
    }

    # Act
    await game_control_handler.handle(sid, data)

    # Assert
    mock_context.auth.validate.assert_called_once_with("valid_token")
    mock_context.scheduler_manager.has_scheduler.assert_called_once_with(game_id)
    mock_context.sio.emit.assert_not_awaited()

    # Verify the token was removed from the payload before publishing
    expected_payload = {
        "game_id": game_id,
        "type": GameEvent.GAME_CONTROL_PAUSE,
        "namespace": namespace,
    }
    mock_context.broker.publish.assert_awaited_once_with(
        game_id, BrokerChannels.CONTROLS, expected_payload
    )
