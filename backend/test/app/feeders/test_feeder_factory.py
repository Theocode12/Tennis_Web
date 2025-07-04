from __future__ import annotations

import logging
from configparser import ConfigParser
from unittest.mock import MagicMock

import pytest

from app.scheduler.game_feeder import FileGameFeeder, RedisGameFeeder
from app.scheduler.game_feeder_factory import create_game_feeder
from db.file_storage import FileStorage
from db.redis_storage import RedisStorageBase as RedisStorage

TEST_GAME_ID = "test_001"


@pytest.fixture
def config_file_feeder() -> ConfigParser:
    config = ConfigParser()
    config.add_section("app")
    config.set("app", "gameFeeder", "file")
    return config


@pytest.fixture
def config_redis_feeder() -> ConfigParser:
    config = ConfigParser()
    config.add_section("app")
    config.set("app", "gameFeeder", "redis")
    return config


def test_create_file_feeder_with_storage(
    config_file_feeder: ConfigParser, dummy_logger: logging.Logger
) -> None:
    mock_storage = MagicMock(spec=FileStorage)
    feeder = create_game_feeder(
        game_id=TEST_GAME_ID,
        config=config_file_feeder,
        logger=dummy_logger,
        filestorage=mock_storage,
    )
    assert isinstance(feeder, FileGameFeeder)
    assert feeder.game_id == TEST_GAME_ID


def test_create_redis_feeder_with_storage(
    config_redis_feeder: ConfigParser, dummy_logger: logging.Logger
) -> None:
    mock_storage = MagicMock(spec=RedisStorage)
    feeder = create_game_feeder(
        game_id=TEST_GAME_ID,
        config=config_redis_feeder,
        logger=dummy_logger,
        redisstorage=mock_storage,
    )
    assert isinstance(feeder, RedisGameFeeder)
    assert feeder.game_id == TEST_GAME_ID


def test_create_file_feeder_without_storage(
    config_file_feeder: ConfigParser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.scheduler import game_feeder_factory

    mock_file_storage = MagicMock()
    monkeypatch.setattr(
        game_feeder_factory, "FileStorage", lambda *a, **kw: mock_file_storage
    )

    feeder = game_feeder_factory.create_game_feeder(TEST_GAME_ID, config_file_feeder)
    assert isinstance(feeder, FileGameFeeder)


def test_create_redis_feeder_without_storage(
    config_redis_feeder: ConfigParser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.scheduler import game_feeder_factory

    mock_redis_storage = MagicMock()
    monkeypatch.setattr(
        game_feeder_factory, "RedisStorage", lambda *a, **kw: mock_redis_storage
    )

    feeder = game_feeder_factory.create_game_feeder(
        TEST_GAME_ID, config_redis_feeder
    )
    assert isinstance(feeder, RedisGameFeeder)


def test_create_feeder_raises_for_invalid_type(dummy_logger: logging.Logger) -> None:
    config = ConfigParser()
    config.add_section("app")
    config.set("app", "gameFeeder", "unsupported")

    with pytest.raises(ValueError, match="Unsupported feeder type 'unsupported'"):
        create_game_feeder(TEST_GAME_ID, config, dummy_logger)


def test_create_feeder_raises_on_config_exception(
    dummy_logger: logging.Logger,
) -> None:
    config = MagicMock(spec=ConfigParser)
    config.get.side_effect = Exception("boom")

    with pytest.raises(
        RuntimeError, match="Failed to retrieve feeder type from config"
    ):
        create_game_feeder(TEST_GAME_ID, config, dummy_logger)
