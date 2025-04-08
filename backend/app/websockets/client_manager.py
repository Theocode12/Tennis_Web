from socketio import AsyncServer
from app.websockets.scheduler import Publisher
from .publisher.message_broker import MessageBroker
class ClientManager:
    def __init__(self, sio: AsyncServer, broker: MessageBroker):
        self.sio = sio
        self.broker = broker

    async def handle_client_event(self, sid: str, data: dict):
        """Receive control commands from a client (pause, resume, etc)."""
        game_id = data["game_id"]
        command = data["command"]  # Ex: {"action": "pause"}
        await self.broker.push_control(game_id, command)

    async def stream_to_room(self, game_id: str, data: dict):
        """Send real-time updates to clients in a game room."""
        await self.sio.emit("game_update", data, room=game_id)

    def register_handlers(self):
        """Register Socket.IO event handlers (called once during startup)."""

        @self.sio.event
        async def join(sid, data):
            # make sure this game_id exists in db
            # make sure a scheduler exist 
            # if scheduler exist, put in the room
            # if scheduler exist but there are no subscribers in publisher then subscribe
            # if game_id exists in db send back game parameters/state
            game_id = data["game_id"]
            await self.sio.enter_room(sid, game_id)

        @self.sio.event
        async def leave(sid, data):
            game_id = data["game_id"]
            await self.sio.leave_room(sid, game_id)

        @self.sio.event
        async def control(sid, data):
            await self.handle_client_event(sid, data)

    def subscribe_to_scheduler(self, game_id: str):
        """Subscribe to game updates and forward to room clients."""

        async def callback(data: dict):
            # <- self is bound to ClientManager
            await self.stream_to_room(game_id, data)

        self.broker.subscribe(game_id, callback)
 