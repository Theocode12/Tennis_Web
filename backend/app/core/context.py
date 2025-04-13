from socketio import AsyncServer
from backend.app.broker.message_broker import MessageBroker
from backend.app.core.ws_auth import AuthService
from backend.app.scheduler.manager import SchedulerManager
from typing import Set, Dict 
import asyncio

class AppContext:
    sio: AsyncServer
    broker: MessageBroker
    auth: AuthService
    scheduler_manager: SchedulerManager
    broker_listener_tasks: Dict[str, asyncio.Task] # Mapping of game_id to asyncio.Task for broker listener tasks
    
    def __init__(self, sio: AsyncServer, broker: MessageBroker, auth: AuthService, scheduler_manager: SchedulerManager):
        self.sio = sio
        self.broker = broker
        self.auth = auth
        self.scheduler_manager = scheduler_manager
        self.broker_listener_tasks = {}
