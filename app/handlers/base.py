from __future__ import annotations

from typing import Any

from app.core.context import AppContext


class BaseHandler:
    def __init__(self, context: AppContext):
        self.context = context

    async def handle(self, sid: str, data: dict[str, Any]) -> None:
        raise NotImplementedError
