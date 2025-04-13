from abc import ABC, abstractmethod
from typing import AsyncIterator, Any, Union

class MessageBroker(ABC):
    @abstractmethod
    async def publish(self, game_id: str, channel: str, message: Any) -> int:
        """Publish message to specific game/channel"""
        pass

    @abstractmethod
    def subscribe(self, game_id: str, channels: Union[str, list[str]]) -> AsyncIterator[Any]:
        """Subscribe to game/channel messages"""
        async def generator():
            yield
        return generator

    @abstractmethod
    async def broadcast(self, channel: str, message: Any) -> int:
        """Broadcast to all subscribers of a channel"""
        pass

    @abstractmethod
    async def shutdown(self):
        """Cleanup resources"""
        pass