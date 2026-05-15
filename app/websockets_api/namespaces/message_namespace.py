from __future__ import annotations

from typing import Any

from app.shared.enums.game_event import GameEvent

from .base_namespace import BaseNamespace


class MessageNamespace(BaseNamespace):  # type: ignore[misc]
    """
    Public, ephemeral chat namespace for live game discussions.

    - Stateless (no persistence)
    - Room-based (one room per game_id)
    - Fire-and-forget messaging
    """

    def __init__(self, namespace: str, context) -> None:
        super().__init__(namespace, context)

        # sid -> {"game_id": str, "username": str}
        self._sessions: dict[str, dict[str, str]] = {}

    # =========================
    # Connection Lifecycle
    # =========================

    async def on_connect(self, sid: str, environ: dict[str, Any]) -> None:
        """
        Accept all connections. No auth.
        """
        self.logger.debug(f"[messages] Client connected: SID={sid}")

    async def on_disconnect(self, sid: str) -> None:
        """
        Cleanup session and update viewer count if needed.
        """
        session = self._sessions.pop(sid, None)

        if not session:
            return

        game_id = session["game_id"]

        self.logger.debug(f"[messages] Client {sid} disconnected from game {game_id}")

        await self.leave_room(sid, game_id)
        await self._emit_viewer_count(game_id)

    # =========================
    # Client Events
    # =========================

    async def on_join(self, sid: str, data: dict[str, Any]) -> None:
        """
        Join a game chat room.

        Expected payload:
        {
            "game_id": "<str>",
            "username": "<optional str>"
        }
        """
        if not isinstance(data, dict):
            await self.emit_error(sid, "Invalid payload.")
            return

        game_id = data.get("game_id")
        if not isinstance(game_id, str) or not game_id.strip():
            await self.emit_error(sid, "Missing or invalid game_id.")
            return

        username = data.get("username")
        if not isinstance(username, str) or not username.strip():
            username = self._default_username(sid)

        # Prevent double-join
        if sid in self._sessions:
            await self.emit_error(sid, "Already joined a game.")
            return

        self._sessions[sid] = {
            "game_id": game_id,
            "username": username.strip()[:32],
        }

        await self.enter_room(sid, game_id)
        self.logger.info(f"[messages] SID={sid} joined game room {game_id} as '{username}'")

        await self._emit_viewer_count(game_id)

    async def on_message(self, sid: str, data: dict[str, Any]) -> None:
        """
        Broadcast a chat message to everyone in the room except the sender.

        Expected payload:
        {
            "text": "<str>"
        }
        """
        session = self._sessions.get(sid)
        if not session:
            await self.emit_error(sid, "You must join a game first.")
            return

        if not isinstance(data, dict):
            await self.emit_error(sid, "Invalid payload.")
            return

        text = data.get("text")
        if not isinstance(text, str) or not text.strip():
            return  # silently ignore empty messages

        message = {
            "user": session["username"],
            "text": text.strip()[:500],
        }

        await self.emit(
            GameEvent.MESSAGE_SEND,
            message,
            room=session["game_id"],
            skip_sid=sid,
        )

    # =========================
    # Internal Helpers
    # =========================

    async def _emit_viewer_count(self, game_id: str) -> None:
        """
        Emit updated viewer count to the game room.
        """
        participants = self.context.client_manager.get_participants(
            self.namespace,
            game_id,
        )

        count = len(list(participants))

        await self.emit(
            GameEvent.VIEWER_COUNT,
            {"count": count},
            room=game_id,
        )

    @staticmethod
    def _default_username(sid: str) -> str:
        return f"Guest-{sid[:6]}"
