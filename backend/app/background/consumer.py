import asyncio
import uuid

import redis.asyncio as redis
from fastapi import FastAPI

from app.background.handlers import handle_command
from app.dependencies import get_redis_client
from utils.load_config import load_config
from utils.logger import get_logger


def make_consumer_name() -> str:
    return f"fastapi-{uuid.uuid4().hex[:8]}"


async def game_command_consumer(app: FastAPI) -> None:
    redis_client: redis.Redis = get_redis_client()
    consumer_name = make_consumer_name()
    config = load_config()
    logger = get_logger()

    STREAM_KEY = config["background"]["STREAM_KEY"]
    CONSUMER_GROUP = config["background"]["CONSUMER_GROUP"]

    try:
        await redis_client.xgroup_create(
            name=STREAM_KEY,
            groupname=CONSUMER_GROUP,
            id="0",
            mkstream=True,
        )
        logger.info(f"Consumer group created: {CONSUMER_GROUP}")
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    while True:
        try:
            response = await redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=consumer_name,
                streams={STREAM_KEY: ">"},
                count=10,
                block=5000,
            )

            if not response:
                continue

            for _, messages in response:
                for message_id, payload in messages:
                    try:
                        await handle_command(app, message_id, payload)
                        await redis_client.xack(
                            STREAM_KEY, CONSUMER_GROUP, message_id
                        )
                    except Exception:
                        logger.exception("Command handling failed")
                        # leave unacked
        except asyncio.CancelledError:
            logger.info("Redis consumer cancelled")
            break
