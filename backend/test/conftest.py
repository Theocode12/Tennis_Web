from __future__ import annotations

import json
import logging
from configparser import ConfigParser
from pathlib import Path
from unittest.mock import patch

import pytest
import redis.asyncio as redis


def is_redis_available():
    """Synchronously check if Redis is available on localhost:6379."""
    import redis as redis_sync

    try:
        client = redis_sync.Redis(host="localhost", port=6379, socket_connect_timeout=1)
        return client.ping()
    except Exception:
        return False


# Session-level availability flag
REDIS_AVAILABLE = is_redis_available()


@pytest.fixture
def is_redis_live():
    """Fixture to check if Redis is available (used by existing tests)."""
    return REDIS_AVAILABLE


@pytest.fixture
def is_redis_available():
    """Fixture alias (used by some newer tests)."""
    return REDIS_AVAILABLE


def pytest_configure(config):
    config.addinivalue_line("markers", "redis: mark test as requiring a running Redis server")


def pytest_runtest_setup(item):
    if any(item.iter_markers(name="redis")):
        if not REDIS_AVAILABLE:
            pytest.skip("Redis server not available at localhost:6379")


@pytest.fixture
def redis_client_sync():
    import redis as redis_sync

    return redis_sync.Redis(host="localhost", port=6379, db=15, decode_responses=True)


@pytest.fixture(autouse=True)
def mock_dependencies(redis_client, redis_client_sync, tmp_path):
    from app import dependencies

    # Create temporary paths for all tests to protect real data
    temp_media = tmp_path / "media_test"
    temp_store = tmp_path / "music_test.json"
    temp_media.mkdir(exist_ok=True)

    with (
        patch("app.dependencies.get_redis_client", return_value=redis_client),
        patch("app.infra.sync_redis.get_redis_client", return_value=redis_client_sync),
        patch("app.dependencies.MEDIA_ROOT", temp_media),
        patch("app.dependencies.MUSIC_STORE_PATH", temp_store),
        patch("app.api.v1.media.UPLOAD_DIR", temp_media),
        patch("app.services.ingestion_service.UPLOAD_DIR", temp_media),
        patch("app.services.ingestion_service.MEDIA_ROOT", temp_media),
    ):
        dependencies.music_service_instance = None
        yield
        dependencies.music_service_instance = None


@pytest.fixture
def dummy_logger() -> logging.Logger:
    logger = logging.getLogger("dummy")
    logger.addHandler(logging.NullHandler())
    return logger


@pytest.fixture
def valid_config(tmp_path: Path) -> ConfigParser:
    config = ConfigParser()
    config["app"] = {
        "gameFeeder": "file",
        "gameDataDir": str(tmp_path / "data" / "games"),
        "gameFileExt": ".json",
        "redisUrl": "redis://localhost:6379/0",
        "messageBroker": "memory",
        "defaultGameSpeed": "1",
        "pauseTimeoutSecs": "60",
        "socketClientManager": "manager",
    }
    return config


@pytest.fixture
async def redis_client():
    client = redis.Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    try:
        await client.ping()
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest.fixture
def mock_media_env(tmp_path: Path):
    media_dir = tmp_path / "media"
    store_dir = tmp_path / "db" / "data"
    media_dir.mkdir()
    store_dir.mkdir(parents=True)

    song_id = "test_song"
    song_dir = media_dir / song_id
    song_dir.mkdir()

    # Create dummy HLS file
    (song_dir / "playlist.m3u8").write_text("#EXTM3U")

    # Create meta.json
    meta = {"title": "Test Song Title", "artist": "Test Artist"}
    (song_dir / "meta.json").write_text(json.dumps(meta))

    # Create music.json store
    music_store = {
        "songs": [
            {
                "id": song_id,
                "title": "Store Title",
                "artist": "Store Artist",
                "stream_url": f"/media/{song_id}/playlist.m3u8",
            }
        ],
        "playlists": [{"id": "test_playlist", "name": "Test Playlist", "songs": [song_id]}],
    }
    store_file = store_dir / "music.json"
    store_file.write_text(json.dumps(music_store, indent=2))

    with patch("app.dependencies.MEDIA_ROOT", media_dir), patch("app.dependencies.MUSIC_STORE_PATH", store_file):
        yield {"media_dir": media_dir, "store_file": store_file, "song_id": song_id, "playlist_id": "test_playlist"}


@pytest.fixture(autouse=True)
async def clear_redis_state():
    client = redis.Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    await client.flushdb()
    await client.aclose()
    yield
    client = redis.Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    await client.flushdb()
    await client.aclose()
