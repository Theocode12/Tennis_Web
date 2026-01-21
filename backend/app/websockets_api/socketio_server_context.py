from __future__ import annotations

import logging
from configparser import ConfigParser

from socketio import AsyncServer

from app.broker.message_broker import MessageBroker
from app.core.ws_auth import AuthService
from app.handlers.broker_relay import BrokerRelay
from app.scheduler.manager import SchedulerManager
from app.websockets_api.namespaces.game_namespace import GameNamespace
from app.websockets_api.routes.router import Router


def bulid_socketio_server_context(
    sio: AsyncServer,
    config: ConfigParser,
    logger: logging.Logger,
) -> SocketIOServerContext:
    from app.broker.message_broker_factory import get_message_broker
    from app.core.ws_auth import AuthService
    from app.handlers.broker_relay import BrokerRelay
    from app.scheduler.manager import SchedulerManager
    from app.websockets_api.routes.router import Router

    broker = get_message_broker(config, logger)
    auth = AuthService()
    router = Router(logger=logger)
    scheduler_manager = SchedulerManager(broker, config=config, logger=logger)
    broker_relay = BrokerRelay(sio, broker, logger)

    return SocketIOServerContext(
        sio=sio,
        broker=broker,
        auth=auth,
        router=router,
        scheduler_manager=scheduler_manager,
        broker_relay=broker_relay,
    )


class SocketIOServerContext:
    def __init__(
        self,
        sio: AsyncServer,
        broker: MessageBroker,
        auth: AuthService,
        router: Router,
        scheduler_manager: SchedulerManager,
        broker_relay: BrokerRelay,
    ) -> None:
        from app.core.context import AppContext

        self.sio = sio
        self.broker = broker
        self.scheduler_manager = scheduler_manager
        self.broker_relay = broker_relay

        self.context = AppContext(
            sio=sio,
            broker=broker,
            auth=auth,
            scheduler_manager=scheduler_manager,
            router=router,
            broker_relay=self.broker_relay,
        )
        router.load_routes()  # move to main later

    def register(self) -> None:
        self.context.sio.register_namespace(GameNamespace("/game", self.context))

    def get_scheduler_manager(self) -> SchedulerManager:
        return self.scheduler_manager

    async def shutdown(self) -> None:
        """
        Gracefully shut down all websocket-related resources.
        """

        await self.scheduler_manager.shutdown()
        await self.broker.shutdown()
        await self.broker_relay.shutdown()
        await self.sio.shutdown()
