from __future__ import annotations

import logging
from configparser import ConfigParser

from app.scheduler.game_feeder import BaseGameFeeder, FileGameFeeder, RedisGameFeeder
from db.file_storage import FileStorage
from db.redis_storage import RedisStorage


def create_game_feeder(
    game_id: str,
    config: ConfigParser,
    logger: logging.Logger | None = None,
    *,
    filestorage: FileStorage | None = None,
    redisstorage: RedisStorage | None = None,
) -> BaseGameFeeder:
    """
    Factory function to create the appropriate GameFeeder instance.

    Args:
        game_id: The unique game identifier.
        config: ConfigParser object containing application settings.
        logger: Optional logger for diagnostic logging.

    Returns:
        BaseGameFeeder: Instance of a concrete feeder implementation.
    """

    logger = logger or logging.getLogger(__name__)

    try:
        feeder_type = (
            config.get("app", "gameFeeder", fallback="file").strip().lower()
        )
    except Exception as e:
        msg = f"Failed to retrieve feeder type from config for game {game_id}: {e}"
        logger.exception(msg)
        raise RuntimeError(msg) from e

    logger.debug(f"Feeder type for game {game_id}: '{feeder_type}'")

    if feeder_type == "redis":
        if not redisstorage:
            logger.debug("No Redis storage provided; initializing new instance.")
            redisstorage = RedisStorage(config, logger)
        return RedisGameFeeder(game_id, redisstorage)

    elif feeder_type == "file":
        if not filestorage:
            logger.debug("No file storage provided; initializing new instance.")
            filestorage = FileStorage(config, logger)
        return FileGameFeeder(game_id, filestorage)

    else:
        msg = f"Unsupported feeder type '{feeder_type}' in config for game {game_id}"
        if logger:
            logger.error(msg)
        raise ValueError(msg)
