from __future__ import annotations

import configparser
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from utils.load_config import load_config
from utils.logger import get_logger

from app.shared.enums.broker_channels import BrokerChannels


class MessageBroker(ABC):
    def __init__(
        self,
        config: configparser.ConfigParser | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.logger = logger or get_logger()
        self.config = config or load_config()

    @abstractmethod
    async def publish(self, game_id: str, channel: str, message: Any) -> int:
        """Publish message to specific game/channel"""
        pass

    @abstractmethod
    async def subscribe(
        self, game_id: str, channels: BrokerChannels | list[BrokerChannels]
    ) -> AsyncGenerator[Any, None]:
        """Subscribe to game/channel messages"""

        async def generator() -> AsyncGenerator[Any, None]:
            yield

        return generator()

    @abstractmethod
    async def broadcast(self, channel: str, message: Any) -> int:
        """Broadcast to all subscribers of a channel"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources"""
        pass
