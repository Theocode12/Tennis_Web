from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.enums.game_event import GameEvent
from app.websockets_api.namespaces.message_namespace import MessageNamespace


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.sio = AsyncMock()
    context.logger = MagicMock()
    return context


@pytest.fixture
def message_namespace(mock_context):
    return MessageNamespace("/messages", mock_context)


@pytest.mark.asyncio
async def test_on_connect(message_namespace):
    await message_namespace.on_connect("sid1", {})
    message_namespace.logger.debug.assert_called()


@pytest.mark.asyncio
async def test_on_join_success(message_namespace, mock_context):
    # Mock _emit_viewer_count to avoid testing it here
    message_namespace._emit_viewer_count = AsyncMock()
    message_namespace.enter_room = AsyncMock()

    data = {"game_id": "game1", "username": "alice"}
    await message_namespace.on_join("sid1", data)

    assert message_namespace._sessions["sid1"] == {
        "game_id": "game1",
        "username": "alice",
    }
    message_namespace.enter_room.assert_awaited_once_with("sid1", "game1")
    message_namespace._emit_viewer_count.assert_awaited_once_with("game1")


@pytest.mark.asyncio
async def test_on_join_default_username(message_namespace, mock_context):
    message_namespace._emit_viewer_count = AsyncMock()
    message_namespace.enter_room = AsyncMock()

    data = {"game_id": "game1"}
    await message_namespace.on_join("sid1", data)

    assert message_namespace._sessions["sid1"]["username"] == "Guest-sid1"
    message_namespace.enter_room.assert_awaited_once_with("sid1", "game1")


@pytest.mark.asyncio
async def test_on_message_success(message_namespace, mock_context):
    message_namespace._sessions["sid1"] = {"game_id": "game1", "username": "alice"}
    message_namespace.emit = AsyncMock()

    data = {"text": "hello world"}
    await message_namespace.on_message("sid1", data)

    message_namespace.emit.assert_awaited_once_with(
        GameEvent.MESSAGE_SEND,
        {"user": "alice", "text": "hello world"},
        room="game1",
        skip_sid="sid1",
    )


@pytest.mark.asyncio
async def test_on_disconnect(message_namespace, mock_context):
    message_namespace._sessions["sid1"] = {"game_id": "game1", "username": "alice"}
    message_namespace._emit_viewer_count = AsyncMock()
    message_namespace.leave_room = AsyncMock()

    await message_namespace.on_disconnect("sid1")

    assert "sid1" not in message_namespace._sessions
    message_namespace.leave_room.assert_awaited_once_with("sid1", "game1")
    message_namespace._emit_viewer_count.assert_awaited_once_with("game1")


@pytest.mark.asyncio
async def test_viewer_count_calculation(message_namespace, mock_context):
    # Mock client_manager.get_participants to return 2 participants
    mock_context.client_manager.get_participants.return_value = ["sid1", "sid2"]
    message_namespace.emit = AsyncMock()

    await message_namespace._emit_viewer_count("game1")

    # count should be 2
    message_namespace.emit.assert_awaited_once_with(
        GameEvent.VIEWER_COUNT, {"count": 2}, room="game1"
    )
