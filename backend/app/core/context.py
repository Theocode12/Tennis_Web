from __future__ import annotations

import asyncio
import configparser
import logging
from typing import TYPE_CHECKING

from socketio import AsyncServer, Manager  # type: ignore
from utils.load_config import load_config
from utils.logger import get_logger

from app.broker.message_broker import MessageBroker
from app.core.ws_auth import AuthService
from app.scheduler.manager import SchedulerManager

if TYPE_CHECKING:
    from app.websockets_api.routes.router import Router


class AppContext:
    sio: AsyncServer
    broker: MessageBroker
    auth: AuthService
    scheduler_manager: SchedulerManager
    router: Router
    client_manager: Manager
    broker_listener_tasks: dict[
        str, asyncio.Task[None]
    ]  # Mapping of game_id to asyncio.Task for broker listener tasks

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
        self.broker_listener_tasks = {}
