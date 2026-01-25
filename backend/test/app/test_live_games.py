from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from configparser import ConfigParser

import pytest
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient

from app.dependencies import close_redis, get_app_config, init_redis
from main import app
from utils.load_config import load_config


# Helper fixture to override dependencies
@pytest.fixture
async def client(valid_config: ConfigParser) -> AsyncGenerator[AsyncClient, None]:
    # Ensure Redis is initialized for the tests
    app.dependency_overrides[load_config] = lambda: valid_config
    app.dependency_overrides[get_app_config] = lambda: valid_config

    await init_redis()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    try:
        await close_redis()
    except RuntimeError:
        # Event loop may already be closed
        pass
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_live_games_empty(client: AsyncClient, is_redis_live: bool):
    if not is_redis_live:
        pytest.skip("Redis is not available")

    response = await client.get("/api/v1/live-games")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["data"] == []


@pytest.mark.asyncio
async def test_get_live_games_filtering(
    client: AsyncClient, is_redis_live: bool, valid_config: ConfigParser
):
    if not is_redis_live:
        pytest.skip("Redis is not available")

    redis_url = valid_config.get("app", "redisUrl")
    r = redis.Redis.from_url(redis_url)

    # Prefix from default fallback in main.py is "live:game:*"
    # Visible states default is "ongoing"

    # 1. Setup Data
    # Game 1: Visible
    game1 = {"game_id": "g1", "game_state": "ongoing", "p1": "Alice", "p2": "Bob"}
    await r.set("live:game:g1", json.dumps(game1))

    # Game 2: Not visible (finished)
    game2 = {
        "game_id": "g2",
        "game_state": "finished",
        "p1": "Charlie",
        "p2": "David",
    }
    await r.set("live:game:g2", json.dumps(game2))

    # Game 3: Malformed JSON
    await r.set("live:game:g3", "{bad-json}")

    # Game 4: Visible
    game4 = {"game_id": "g4", "game_state": "ongoing", "score": "15-30"}
    await r.set("live:game:g4", json.dumps(game4))

    try:
        # 2. Call Endpoint
        response = await client.get("/api/v1/live-games?limit=10")
        assert response.status_code == 200
        data = response.json()

        # 3. Verify
        # Should return g1 and g4. g2 is finished, g3 is invalid.
        assert data["total"] == 2

        # Check that we got the correct games
        game_ids = {g["game_id"] for g in data["data"]}
        assert "g1" in game_ids
        assert "g4" in game_ids
        assert "g2" not in game_ids

    finally:
        # Cleanup
        await r.flushdb()
        await r.aclose()


@pytest.mark.asyncio
async def test_get_live_games_limit(
    client: AsyncClient, is_redis_live: bool, valid_config: ConfigParser
):
    if not is_redis_live:
        pytest.skip("Redis is not available")

    redis_url = valid_config.get("app", "redisUrl")
    r = redis.Redis.from_url(redis_url)

    # Insert 5 visible games
    for i in range(5):
        game = {"game_id": f"g{i}", "game_state": "ongoing"}
        await r.set(f"live:game:limit:{i}", json.dumps(game))

    try:
        # Request limit=3
        response = await client.get("/api/v1/live-games?limit=3")
        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) == 3
        # Total field in response reflects returned count, NOT total in DB
        # (based on code: "total": len(results))
        assert data["total"] == 3

    finally:
        await r.flushdb()
        await r.aclose()
