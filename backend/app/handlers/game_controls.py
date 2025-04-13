from .auth_base import AuthenticatedHandler
from app.websockets_api.routes.registry import register_route
from pydantic import BaseModel, Field
from typing import Literal
from backend.app.shared.enums.message_types import MessageType


class GameControlHandler(AuthenticatedHandler):
    async def handle_authenticated(self, sid: str, data: dict):
        game_id = data["game_id"]
        await self.context.broker.publish(game_id, 'controls', data)

class GameControlSchema(BaseModel):
    game_id: str
    token: str
    type: Literal[
        MessageType.GAME_CONTROL_START,
        MessageType.GAME_CONTROL_PAUSE,
        MessageType.GAME_CONTROL_RESUME
    ]

class StartControlHandler(GameControlHandler):
    async def handle_authenticated(self, sid, data):
        return await super().handle_authenticated(sid, data)

class PauseControlHandler(GameControlHandler):
    async def handle_authenticated(self, sid, data):
        return await super().handle_authenticated(sid, data)
    
class ResumeControlHandler(GameControlHandler):
    async def handle_authenticated(self, sid, data):
        return await super().handle_authenticated(sid, data)
    
class SpeedControlHandler(GameControlHandler):
    async def handle_authenticated(self, sid, data):
        return await super().handle_authenticated(sid, data)
    
class SpeedControlSchema(BaseModel):
    game_id: str
    token: str 
    speed: int = Field(..., ge=1, le=7)
    type: Literal[MessageType.GAME_CONTROL_SPEED]
    
register_route(message_type=MessageType.GAME_CONTROL_START, handler=StartControlHandler, schema=GameControlSchema)
register_route(message_type=MessageType.GAME_CONTROL_PAUSE, handler=PauseControlHandler, schema=GameControlSchema)
register_route(message_type=MessageType.GAME_CONTROL_RESUME, handler=ResumeControlHandler, schema=GameControlSchema)
register_route(message_type=MessageType.GAME_CONTROL_SPEED, handler=SpeedControlHandler, schema=SpeedControlSchema)
