from typing import Any, Callable, Coroutine
from ..publisher.message_broker import MessageBroker

class BaseScheduler:
    def __init__(self, game_id, broker: MessageBroker):
        self.game_id = game_id
        self.publisher = broker

    async def publish(self, channel, message):
        """Publish data to the game channel."""
        return await self.publisher.publish(self.game_id, channel, message)

    def subscribe(self, channel):
        pass
    
    async def cleanup(self):
        pass

class ControlScheduler(BaseScheduler):
    async def start(self):
        pass

    async def pause(self):
        pass

    async def resume(self):
        pass

    async def adjust_speed(self, new_speed):
        pass


class PvAIScheduler(ControlScheduler):
    pass

class PvPControlScheduler(ControlScheduler):
    pass

class SpectatorScheduler(BaseScheduler):
    pass
