from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from app.background.handlers import handle_command, handle_start_stream


@pytest.fixture
def mock_app():
    app = MagicMock(spec=FastAPI)
    app.state = MagicMock()

    mock_sio_context = MagicMock()
    app.state.sio_context = mock_sio_context

    mock_scheduler_manager = MagicMock()
    mock_sio_context.get_scheduler_manager.return_value = mock_scheduler_manager

    return app, mock_scheduler_manager


@pytest.mark.asyncio
@patch("app.background.handlers.handle_start_stream")
async def test_handle_command_dispatch(mock_handle_start, mock_app):
    app, _ = mock_app

    # Test START_STREAM dispatch
    payload = {"type": "START_STREAM", "match_id": "test-match"}
    await handle_command(app, "msg-1", payload)
    mock_handle_start.assert_called_once_with(app, payload)


@pytest.mark.asyncio
@patch("app.background.handlers.logger")
async def test_handle_command_unknown(mock_logger, mock_app):
    app, _ = mock_app

    payload = {"type": "UNKNOWN_ACTION"}
    await handle_command(app, "msg-2", payload)

    mock_logger.warning.assert_called_once()
    assert "Unknown command type" in mock_logger.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_start_stream_success(mock_app):
    app, mock_manager = mock_app

    # Mock scheduler
    mock_scheduler = AsyncMock()
    mock_manager.create_or_get_scheduler = AsyncMock(return_value=(mock_scheduler, True))

    payload = {"match_id": "match-123"}
    await handle_start_stream(app, payload)

    # Verify manager called correctly
    mock_manager.create_or_get_scheduler.assert_called_once_with(game_id="match-123")
    # Verify scheduler started
    mock_scheduler.start.assert_called_once()


@pytest.mark.asyncio
async def test_handle_start_stream_missing_id(mock_app):
    app, _ = mock_app

    payload = {"no_id": "here"}
    with pytest.raises(ValueError, match="Missing match_id"):
        await handle_start_stream(app, payload)
