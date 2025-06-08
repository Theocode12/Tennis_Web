from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Awaitable
from configparser import ConfigParser
from typing import Any, cast

import pytest

from app.scheduler.game_feeder import RedisGameFeeder
from db.redis_storage import RedisStorageBase as RedisStorage

TEST_GAME_ID = "redis_game_123"
TEST_SCORES_LIST = [
    {"set": [[0], [0]], "game_points": [0, 1]},
    {"set": [[0], [0]], "game_points": [0, 2]},
    {"set": [[0], [0]], "game_points": [0, 3]},
]
TEST_GAME_DETAILS = {
    "game_id": TEST_GAME_ID,
    "teams": {
        "team_1": {"name": "Team A", "players": [{"name": "Alice"}]},
        "team_2": {"name": "Team B", "players": [{"name": "Bob"}]},
    },
}


@pytest.fixture
async def game_feeder(
    is_redis_live: bool, valid_config: ConfigParser, dummy_logger: logging.Logger
) -> AsyncGenerator[RedisGameFeeder, Any]:
    if not is_redis_live:
        pytest.skip("Skipping test: Redis not running.")
    storage = RedisStorage(valid_config, dummy_logger)
    await storage.connect()
    client = await storage.get_client()
    scores_key = f"{TEST_GAME_ID}:scores"

    # Setup test data
    await client.set(TEST_GAME_ID, json.dumps(TEST_GAME_DETAILS))
    await client.delete(scores_key)
    for score in TEST_SCORES_LIST:
        rpush_call = client.rpush(scores_key, json.dumps(score))
        await cast(Awaitable[int], rpush_call)
    yield RedisGameFeeder(TEST_GAME_ID, storage, logger=dummy_logger, batch_size=1)

    await client.delete(TEST_GAME_ID)
    await client.delete(f"{TEST_GAME_ID}:scores")


@pytest.mark.asyncio
async def test_get_game_details_from_redis(game_feeder: RedisGameFeeder) -> None:
    details = await game_feeder.get_game_details()
    assert details == TEST_GAME_DETAILS


@pytest.mark.asyncio
async def test_live_load_and_fetch_scores(game_feeder: RedisGameFeeder) -> None:
    score_iter = game_feeder.get_next_score()
    results = []
    async for score in score_iter:
        results.append(score)

    assert results == TEST_SCORES_LIST
    assert game_feeder._exhausted is True
    assert len(game_feeder._buffer) == 0
