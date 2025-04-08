from abc import ABC, abstractmethod
from asyncio import Event
from typing import Any, Callable, Coroutine
from ..publisher.message_broker import MessageBroker

class BaseScheduler(ABC):
    def __init__(self, game_id, broker: MessageBroker):
        self.game_id = game_id
        self.broker = broker

    async def publish(self, channel, message):
        """Publish data to the game channel."""
        return await self.broker.publish(self.game_id, channel, message)

    async def run(self):
        raise NotImplementedError
    
    async def cleanup(self):
        pass

class ControlScheduler(BaseScheduler):
    def __init__(self, game_id, broker):
        super().__init__(game_id, broker)
        self.event = Event()
        self.speed = 1 # in secs
        self.controls = {
            'start': self.start,
            'pause': self.pause,
            'resume': self.resume,
            'adjust_speed': self.adjust_speed
        }

    async def start(self):
        self.event.set()

    async def pause(self):
        self.event.clear()

    async def resume(self):
        self.event.set()

    async def adjust_speed(self, new_speed):
        self.speed = new_speed

    async def subscribe(self, channel):
        async for message in self.broker.subscribe(self.game_id, channel):
            if message.get('type') and (control := self.controls.get(message.get('type'))):
                await control()


class PvAIScheduler(ControlScheduler):
    def run():
        pass
    

class PvPControlScheduler(ControlScheduler):
    def run():
        pass

class SpectatorScheduler(BaseScheduler):
    def run():
        pass
