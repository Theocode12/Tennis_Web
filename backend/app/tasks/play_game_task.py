from __future__ import annotations

from gameengine import GameBuilder, GameRunner
from utils.logger import get_logger
from typing import Any
from configparser import ConfigParser
from app.celery import app
import asyncio


@app.task()  # type: ignore
def play_game_task(match_spec: dict[str, Any], game_config: dict[str, Any]) -> str:
    try:
        config = ConfigParser()
        config.read_dict(game_config)
        print("Playing game with data:", match_spec)

        gb = GameBuilder(match_spec, get_logger(config=config), config)
        loop = asyncio.get_event_loop()

        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(GameRunner(gb).run())
    except Exception as e:
        raise e

    # Simulate game processing
    return "Game finished"
