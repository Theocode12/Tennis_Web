from __future__ import annotations

import configparser
import logging

from app.broker.message_broker import MessageBroker


def get_message_broker(
    config: configparser.ConfigParser, logger: logging.Logger
) -> MessageBroker:
    """
    Factory function to create a MessageBroker instance based on the configuration.

    Args:
        config: ConfigParser object containing application settings.
        logger: Logger instance for diagnostic logging.

    Returns:
        MessageBroker: Instance of the configured message broker.
    """

    try:
        broker_type = (
            config.get("app", "messageBroker", fallback="redis").strip().lower()
        )
    except Exception as e:
        msg = f"Failed to retrieve broker type from config: {e}"
        logger.exception(msg)
        raise RuntimeError(msg) from e

    logger.debug(f"Message broker type: '{broker_type}'")

    if broker_type == "redis":
        from app.broker.redis_message_broker import RedisMessageBroker

        return RedisMessageBroker(config, logger)

    elif broker_type == "memory":
        from app.broker.memory_message_broker import InMemoryMessageBroker

        return InMemoryMessageBroker(config, logger)

    else:
        msg = f"Unsupported message broker type '{broker_type}' in config"
        logger.error(msg)
        raise ValueError(msg)
