from socketio import AsyncServer
from backend.app.broker.message_broker import MessageBroker
from backend.app.core.context import AppContext
from backend.app.core.ws_auth import AuthService
from app.websockets_api.routes import loader
from backend.app.scheduler.manager import SchedulerManager
from app.websockets_api.namespaces.game_namespace import GameNamespace


class ClientManager:
    def __init__(self, sio: AsyncServer, broker: MessageBroker, auth: AuthService, scheduler_manager: SchedulerManager):
        self.context = AppContext(sio=sio, broker=broker, auth=auth, scheduler_manager=scheduler_manager)
        loader.load_routes() #move to main later

    def register(self):
        self.context.sio.register_namespace(GameNamespace('/game', self.context))