from .base import BaseHandler

class AuthenticatedHandler(BaseHandler):
    async def handle(self, sid: str, data: dict):
        token = data.get("token")
        if not self.context.auth.validate(token):
            await self.context.sio.emit("auth_error", {"error": "Unauthorized"}, to=sid)
            return
        await self.handle_authenticated(sid, data)

    async def handle_authenticated(self, sid: str, data: dict):
        raise NotImplementedError
