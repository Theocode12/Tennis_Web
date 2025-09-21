from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest import MonkeyPatch

from app.exceptions.message_error import MessageError
from app.shared.enums.game_event import GameEvent
from app.websockets_api.namespaces.base_namespace import BaseNamespace
from app.websockets_api.namespaces.game_namespace import GameNamespace
from app.websockets_api.namespaces.message_dispacter import MessageDispatcher


@pytest.mark.asyncio
async def test_on_message_dispatch_success(monkeypatch: MonkeyPatch) -> None:
    """Test that on_message calls dispatcher and emits nothing on success."""
    mock_dispatcher = AsyncMock()
    mock_emit = AsyncMock()

    context = MagicMock()
    context.logger = MagicMock()

    namespace = BaseNamespace("/game", context)
    namespace.dispatcher = mock_dispatcher
    namespace.emit = mock_emit

    data = {"type": GameEvent.GAME_JOIN.value, "player": "alice"}
    sid = "session1"

    await namespace.on_message(sid, data)

    mock_dispatcher.dispatch.assert_awaited_once_with(sid, data, "/game")
    mock_emit.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_message_invalid_data_type_triggers_error() -> None:
    """Non-dict payload raises MessageError and emits ERROR event."""
    context = MagicMock()
    context.logger = MagicMock()

    namespace = BaseNamespace("/game", context)
    namespace.dispatcher = MagicMock()
    namespace.emit = AsyncMock()

    sid = "session1"
    data = ["not", "a", "dict"]

    await namespace.on_message(sid, data)

    namespace.emit.assert_awaited_once()
    args, kwargs = namespace.emit.call_args
    assert args[0] == GameEvent.ERROR.value
    assert type(args[1]) is dict
    assert "error" in args[1].keys()
    assert kwargs.get("to") == sid


@pytest.mark.asyncio
async def test_on_message_dispatch_raises_message_error() -> None:
    """Dispatcher raises MessageError -> emits ERROR event."""
    mock_dispatcher = AsyncMock()
    mock_dispatcher.dispatch.side_effect = MessageError("Bad message")

    context = MagicMock()
    context.logger = MagicMock()

    namespace = BaseNamespace("/game", context)
    namespace.dispatcher = mock_dispatcher
    namespace.emit = AsyncMock()

    data = {"type": GameEvent.GAME_JOIN.value}
    sid = "sid123"

    await namespace.on_message(sid, data)

    namespace.emit.assert_awaited_once()
    args, kwargs = namespace.emit.call_args
    assert args[0] == GameEvent.ERROR.value


@pytest.mark.asyncio
async def test_dispatch_success() -> None:
    """Test dispatcher calls the correct handler with validated data."""
    # Mock context and router
    mock_context = MagicMock()
    mock_handler = AsyncMock()
    mock_context.router.get_definition.return_value = {
        "handler": lambda ctx: mock_handler,
        "schema": None,
    }

    dispatcher = MessageDispatcher(mock_context)

    sid = "sid1"
    namespace = "/game"
    payload = {"type": GameEvent.GAME_JOIN.value, "player": "alice"}

    await dispatcher.dispatch(sid, payload, namespace)

    mock_context.router.get_definition.assert_called_once_with(GameEvent.GAME_JOIN)
    mock_handler.handle.assert_awaited_once()
    called_sid, called_data = mock_handler.handle.call_args[0][:2]
    assert called_sid == sid
    assert called_data["player"] == "alice"
    assert called_data["namespace"] == namespace


@pytest.mark.asyncio
async def test_dispatch_unknown_event_raises() -> None:
    """Dispatcher raises MessageError on unknown event."""
    mock_context = MagicMock()
    mock_context.router.get_definition.return_value = None
    dispatcher = MessageDispatcher(mock_context)

    sid = "sid1"
    namespace = "/game"
    payload = {"type": "unknown.event"}

    with pytest.raises(MessageError) as exc:
        await dispatcher.dispatch(sid, payload, namespace)

    assert "Unknown event type" in str(exc.value)


@pytest.mark.asyncio
async def test_dispatch_invalid_schema_raises() -> None:
    """Dispatcher raises MessageError if schema validation fails."""
    from pydantic import BaseModel

    class Schema(BaseModel):
        player: str

    class FailingHandler:
        def __init__(self, ctx: MagicMock):
            self.ctx = ctx

        async def handle(self, sid: str, data: dict[str, Any]) -> None:
            return

    mock_context = MagicMock()
    mock_context.router.get_definition.return_value = {
        "handler": FailingHandler,
        "schema": Schema,
    }

    dispatcher = MessageDispatcher(mock_context)

    payload = {"type": GameEvent.GAME_JOIN.value, "invalid_field": 123}
    sid = "sid1"
    namespace = "/game"

    with pytest.raises(MessageError) as exc:
        await dispatcher.dispatch(sid, payload, namespace)

    assert "Invalid data schema" in str(exc.value)


@pytest.mark.asyncio
async def test_dispatch_valid_schema_success() -> None:
    """Dispatcher successfully validates schema and calls handler."""
    from pydantic import BaseModel

    class Schema(BaseModel):
        player: str

    mock_handler = AsyncMock()
    mock_context = MagicMock()
    mock_context.router.get_definition.return_value = {
        "handler": lambda ctx: mock_handler,
        "schema": Schema,
    }

    dispatcher = MessageDispatcher(mock_context)

    payload = {
        "type": GameEvent.GAME_JOIN.value,
        "player": "alice",
        "extra": "field",
    }
    sid = "sid1"
    namespace = "/game"

    await dispatcher.dispatch(sid, payload, namespace)

    mock_handler.handle.assert_awaited_once()
    _sid, validated_data = mock_handler.handle.call_args.args
    assert _sid == sid
    assert validated_data == {"player": "alice", "namespace": "/game"}


@pytest.mark.asyncio
async def test_on_disconnect_leaves_room_but_not_empty() -> None:
    """Test on_disconnect leaves room, but doesn't close it if not empty."""
    sid = "sid1"
    room = "game1"
    namespace_str = "/game"

    mock_context = MagicMock()
    mock_context.sio.rooms.return_value = [sid, room]
    mock_context.client_manager.get_participants.return_value = ["another_sid"]
    mock_context.logger = MagicMock()

    namespace = GameNamespace(namespace_str, mock_context)
    namespace.leave_room = AsyncMock()
    namespace.close_room = AsyncMock()

    await namespace.on_disconnect(sid)

    mock_context.sio.rooms.assert_called_once_with(sid, namespace=namespace_str)
    namespace.leave_room.assert_awaited_once_with(sid, room)
    mock_context.client_manager.get_participants.assert_called_once_with(
        namespace_str, room
    )
    namespace.close_room.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_disconnect_closes_empty_room() -> None:
    """Test on_disconnect leaves room and closes it when it becomes empty."""
    sid = "sid1"
    room = "game1"
    namespace_str = "/game"

    mock_context = MagicMock()
    mock_context.sio.rooms.return_value = [sid, room]
    mock_context.client_manager.get_participants.return_value = []
    mock_context.logger = MagicMock()

    namespace = GameNamespace(namespace_str, mock_context)
    namespace.leave_room = AsyncMock()
    namespace.close_room = AsyncMock()

    await namespace.on_disconnect(sid)

    mock_context.sio.rooms.assert_called_once_with(sid, namespace=namespace_str)
    namespace.leave_room.assert_awaited_once_with(sid, room)
    mock_context.client_manager.get_participants.assert_called_once_with(
        namespace_str, room
    )
    namespace.close_room.assert_awaited_once_with(room)


@pytest.mark.asyncio
async def test_on_disconnect_no_custom_rooms() -> None:
    """Test on_disconnect does nothing if client is only in their own room."""
    sid = "sid1"
    namespace_str = "/game"

    mock_context = MagicMock()
    mock_context.sio.rooms.return_value = [sid]
    mock_context.logger = MagicMock()

    namespace = GameNamespace(namespace_str, mock_context)
    namespace.leave_room = AsyncMock()
    namespace.close_room = AsyncMock()

    await namespace.on_disconnect(sid)

    namespace.leave_room.assert_not_awaited()
    namespace.close_room.assert_not_awaited()
    mock_context.client_manager.get_participants.assert_not_called()


@pytest.mark.asyncio
async def test_on_disconnect_handles_exception() -> None:
    """Test on_disconnect logs an error if an exception occurs."""
    mock_context = MagicMock()
    mock_context.sio.rooms.side_effect = Exception("Test error")
    namespace = GameNamespace("/game", mock_context)
    await namespace.on_disconnect("sid1")
    mock_context.logger.error.assert_called_once()
