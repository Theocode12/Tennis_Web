from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from configparser import ConfigParser
from typing import Any

import pytest

from app.broker.redis_message_broker import RedisMessageBroker
from app.shared.enums.broker_channels import BrokerChannels


@pytest.fixture
async def live_redis_broker(
    is_redis_live: bool, valid_config: ConfigParser, dummy_logger: logging.Logger
) -> AsyncGenerator[RedisMessageBroker, None]:
    if not is_redis_live:
        pytest.skip("Redis server is not available — skipping live Redis tests.")

    broker = RedisMessageBroker(config=valid_config, logger=dummy_logger)
    await broker.connect()
    yield broker
    await broker.shutdown()


@pytest.mark.asyncio
async def test_publish_and_subscribe(live_redis_broker: RedisMessageBroker) -> None:
    game_id = str(uuid.uuid4())
    channel = BrokerChannels.SCORES_UPDATE
    test_data = {"event": "test", "payload": "hello"}

    async def listener() -> Any:
        # Start the subscription process
        gen = await live_redis_broker.subscribe(
            game_id, [BrokerChannels.SCORES_UPDATE]
        )
        try:
            async for message in gen:
                return message
        except Exception as e:
            pytest.fail(f"Unexpected error while listening for message: {e!s}")

    # Start listener
    listener_task = asyncio.create_task(listener())

    # Wait briefly for subscription to register
    await asyncio.sleep(0.1)

    # Publish message
    await live_redis_broker.publish(game_id, channel, test_data)

    # Receive message
    message = await listener_task
    assert message == test_data
