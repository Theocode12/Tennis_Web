from __future__ import annotations

import logging
from configparser import ConfigParser
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.broker.message_broker_factory import get_message_broker


@pytest.fixture
def config_memory_broker() -> ConfigParser:
    config = ConfigParser()
    config.add_section("app")
    config.set("app", "messageBroker", "memory")
    return config


@pytest.fixture
def config_redis_broker() -> ConfigParser:
    config = ConfigParser()
    config.add_section("app")
    config.set("app", "messageBroker", "redis")
    return config


def test_create_memory_broker(
    config_memory_broker: ConfigParser,
    dummy_logger: logging.Logger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_broker = SimpleNamespace(name="MockMemoryBroker")

    def mock_in_memory_broker(
        config: ConfigParser, logger: logging.Logger
    ) -> SimpleNamespace:
        assert config is config_memory_broker
        assert logger is dummy_logger
        return mock_broker

    import app.broker.message_broker_factory as factory_module

    monkeypatch.setattr(
        factory_module, "InMemoryMessageBroker", mock_in_memory_broker
    )

    broker = get_message_broker(config_memory_broker, dummy_logger)
    assert broker is mock_broker


def test_create_redis_broker(
    config_redis_broker: ConfigParser,
    dummy_logger: logging.Logger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_broker = SimpleNamespace(name="MockRedisBroker")

    def mock_redis_broker(
        config: ConfigParser, logger: logging.Logger
    ) -> SimpleNamespace:
        assert config is config_redis_broker
        assert logger is dummy_logger
        return mock_broker

    import app.broker.message_broker_factory as factory_module

    monkeypatch.setattr(factory_module, "RedisMessageBroker", mock_redis_broker)

    broker = get_message_broker(config_redis_broker, dummy_logger)
    assert broker is mock_broker


def test_get_broker_raises_for_invalid_type(
    dummy_logger: logging.Logger,
) -> None:
    config = ConfigParser()
    config.add_section("app")
    config.set("app", "messageBroker", "unsupported")

    with pytest.raises(
        ValueError, match="Unsupported message broker type 'unsupported'"
    ):
        get_message_broker(config, dummy_logger)


def test_get_broker_raises_on_config_exception(
    dummy_logger: logging.Logger,
) -> None:
    config = MagicMock(spec=ConfigParser)
    config.get.side_effect = Exception("boom")

    with pytest.raises(
        RuntimeError, match="Failed to retrieve broker type from config"
    ):
        get_message_broker(config, dummy_logger)
