from __future__ import annotations

from typing import Any

from app.shared.enums.client_events import ClientEvent

from .base import BaseHandler


class AuthenticatedHandler(BaseHandler):
    async def handle(self, sid: str, data: dict[str, Any]) -> None:
        token: str = data.get("token", "")
        if not self.context.auth.validate(token):
            await self.context.sio.emit(
                ClientEvent.ERROR, {"error": "Unauthorized"}, to=sid
            )
            return
        await self.handle_authenticated(sid, data)

    async def handle_authenticated(self, sid: str, data: dict[str, Any]) -> None:
        raise NotImplementedError
