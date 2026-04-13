import asyncio

import redis.asyncio as redis
from fastapi import FastAPI

from app.background.handlers import handle_command
from app.dependencies import get_redis_client
from utils.load_config import load_config
from utils.logger import get_logger


def make_consumer_name() -> str:
    import os
    import socket

    return f"{socket.gethostname()}-{os.getpid()}"


async def game_command_consumer(app: FastAPI) -> None:
    redis_client: redis.Redis = get_redis_client()
    consumer_name = make_consumer_name()
    config = load_config()
    logger = get_logger()

    STREAM_KEY = config["background"]["StreamKey"]
    CONSUMER_GROUP = config["background"]["ConsumerGroup"]

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
                        logger.info(
                            "Processing command %s from stream %s for payload %s",
                            message_id,
                            STREAM_KEY,
                            payload,
                        )
                        await handle_command(app, message_id, payload)
                        await redis_client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
                    except Exception:
                        logger.exception("Command handling failed")
                        # leave unacked
        except asyncio.CancelledError:
            logger.info("Redis consumer cancelled")
            break

        except Exception as e:
            logger.exception("Redis consumer error: %s", str(e))
            break

    try:
        await redis_client.xgroup_delconsumer(
            STREAM_KEY,
            CONSUMER_GROUP,
            consumer_name,
        )
        logger.info(
            "Deleted Redis consumer '%s' from group '%s'",
            consumer_name,
            CONSUMER_GROUP,
        )
    except Exception:
        logger.exception("Failed to delete Redis consumer")
