from __future__ import annotations

import configparser
import logging
from typing import TYPE_CHECKING

from socketio import AsyncServer, Manager  # type: ignore

from app.broker.message_broker import MessageBroker
from app.core.ws_auth import AuthService
from app.handlers.broker_relay import BrokerRelay
from app.scheduler.manager import SchedulerManager
from utils.load_config import load_config
from utils.logger import get_logger

if TYPE_CHECKING:
    from app.websockets_api.routes.router import Router


class AppContext:
    sio: AsyncServer
    broker: MessageBroker
    auth: AuthService
    scheduler_manager: SchedulerManager
    broker_relay: BrokerRelay
    router: Router
    client_manager: Manager

    def __init__(
        self,
        sio: AsyncServer,
        broker: MessageBroker,
        auth: AuthService,
        router: Router,
        scheduler_manager: SchedulerManager,
        config: configparser.ConfigParser | None = None,
        logger: logging.Logger | None = None,
    ):
        self.sio = sio
        self.auth = auth
        self.broker = broker
        self.config = config or load_config()
        self.router = router
        self.logger = logger or get_logger()
        self.scheduler_manager = scheduler_manager
        self.client_manager = self.sio.manager
        self.broker_relay = BrokerRelay(self)
