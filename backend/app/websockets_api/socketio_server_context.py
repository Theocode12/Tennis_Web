from __future__ import annotations

from socketio import AsyncServer

from app.broker.message_broker import MessageBroker
from app.core.ws_auth import AuthService
from app.scheduler.manager import SchedulerManager
from app.websockets_api.namespaces.game_namespace import GameNamespace
from app.websockets_api.routes.router import Router


class SocketIOServerContext:
    def __init__(
        self,
        sio: AsyncServer,
        broker: MessageBroker,
        auth: AuthService,
        router: Router,
        scheduler_manager: SchedulerManager,
    ) -> None:
        from app.core.context import AppContext

        self.context = AppContext(
            sio=sio,
            broker=broker,
            auth=auth,
            scheduler_manager=scheduler_manager,
            router=router,
        )
        router.load_routes()  # move to main later

    def register(self) -> None:
        self.context.sio.register_namespace(GameNamespace("/game", self.context))
