from __future__ import annotations

import logging
from configparser import ConfigParser
from pathlib import Path

from db.file_storage import FileStorage

# --- Tests --- #


def test_initialization_creates_directory(
    valid_config: ConfigParser, dummy_logger: logging.Logger
) -> None:
    path = Path(valid_config.get("app", "gameDataDir"))
    assert not path.exists()

    FileStorage(valid_config, dummy_logger)

    assert path.exists()
    assert path.is_dir()


def test_initialization_with_existing_directory(
    valid_config: ConfigParser, dummy_logger: logging.Logger
) -> None:
    path = Path(valid_config.get("app", "gameDataDir"))
    path.mkdir(parents=True)
    assert path.exists()

    FileStorage(valid_config, dummy_logger)

    assert path.exists()
    assert path.is_dir()


def test_initialization_custom_extension(
    valid_config: ConfigParser, dummy_logger: logging.Logger
) -> None:
    valid_config.set("app", "gameFileExt", ".data")

    FileStorage(valid_config, dummy_logger)

    assert Path(valid_config.get("app", "gameDataDir")).exists()


def test_get_game_path_default_settings(
    valid_config: ConfigParser, dummy_logger: logging.Logger
) -> None:
    storage = FileStorage(valid_config, dummy_logger)
    game_id = "game123"

    expected_path = Path(valid_config.get("app", "gameDataDir")) / f"{game_id}.json"
    actual_path = storage.get_game_path(game_id)

    assert isinstance(actual_path, Path)
    assert actual_path == expected_path


def test_get_game_path_custom_settings(
    valid_config: ConfigParser, dummy_logger: logging.Logger
) -> None:
    valid_config.set("app", "gameFileExt", ".gamedata")

    storage = FileStorage(valid_config, dummy_logger)
    game_id = "alpha_beta"

    expected_path = (
        Path(valid_config.get("app", "gameDataDir")) / f"{game_id}.gamedata"
    )
    actual_path = storage.get_game_path(game_id)

    assert actual_path == expected_path


def test_get_game_path_different_ids(
    valid_config: ConfigParser, dummy_logger: logging.Logger
) -> None:
    storage = FileStorage(valid_config, dummy_logger)

    id1, id2 = "game1", "game2"
    path1 = storage.get_game_path(id1)
    path2 = storage.get_game_path(id2)

    assert path1 != path2
    assert path1.name.endswith(".json")
    assert path2.name.endswith(".json")
    assert path1.name == "game1.json"
    assert path2.name == "game2.json"
