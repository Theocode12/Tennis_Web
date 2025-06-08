from __future__ import annotations

import json
import logging
from collections import deque
from configparser import ConfigParser
from pathlib import Path

import pytest

from app.scheduler.game_feeder import BaseGameFeeder, FileGameFeeder
from db.file_storage import FileStorage  # adjust import if needed

TEST_GAME_ID = "test_123"
TEST_SCORES_LIST = [
    {"set": [[0], [0]], "game_points": [1, 0]},
    {"set": [[0], [0]], "game_points": [1, 1]},
    {"set": [[0], [0]], "game_points": [1, 2]},
    {"set": [[0], [0]], "game_points": [1, 3]},
    {"set": [[0], [0]], "game_points": [2, 3]},
    {"set": [[0], [0]], "game_points": [3, 3]},
    {"set": [[0], [0]], "game_points": [3, 4]},
    {"set": [[0], [0]], "game_points": [3, 5]},
    {"set": [[0], [1]], "game_points": [0, 1]},
]

TEST_GAME_DATA = {
    "game_id": TEST_GAME_ID,
    "teams": {
        "team_1": {"name": "Team A", "players": [{"name": "Alice"}]},
        "team_2": {"name": "Team B", "players": [{"name": "Bob"}]},
    },
    "scores": TEST_SCORES_LIST,
}


@pytest.fixture
def file_game_feeder(
    tmp_path: Path,
    dummy_logger: logging.Logger,
    valid_config: ConfigParser,
) -> FileGameFeeder:
    """Fixture to create a FileGameFeeder with test data."""
    game_dir = tmp_path / "data" / "games"
    game_dir.mkdir(parents=True, exist_ok=True)

    file_path = game_dir / f"{TEST_GAME_ID}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(TEST_GAME_DATA, f)

    storage = FileStorage(valid_config, dummy_logger)
    feeder = FileGameFeeder(
        game_id=TEST_GAME_ID, storage=storage, logger=dummy_logger
    )
    return feeder


@pytest.mark.asyncio
async def test_initialization(file_game_feeder: FileGameFeeder) -> None:
    feeder = file_game_feeder
    assert isinstance(feeder, BaseGameFeeder)
    assert feeder.game_id == TEST_GAME_ID
    assert isinstance(feeder._buffer, deque)
    assert len(feeder._buffer) == 0
    assert not feeder._exhausted
    assert feeder.file_path.exists()


@pytest.mark.asyncio
async def test_load_batch_populates_buffer_and_exhausts(
    file_game_feeder: FileGameFeeder,
) -> None:
    feeder = file_game_feeder
    assert not feeder._exhausted
    assert len(feeder._buffer) == 0

    score_iterator = feeder.get_next_score()
    first_score = await score_iterator.__anext__()

    assert first_score == TEST_SCORES_LIST[0]
    assert feeder._exhausted
    assert len(feeder._buffer) == len(TEST_SCORES_LIST) - 1
    assert feeder._buffer == deque(TEST_SCORES_LIST[1:])


@pytest.mark.asyncio
async def test_get_next_score_yields_all_scores_in_order(
    file_game_feeder: FileGameFeeder,
) -> None:
    feeder = file_game_feeder
    collected_scores = []

    async for score in feeder.get_next_score():
        collected_scores.append(score)

    assert collected_scores == TEST_SCORES_LIST
    assert feeder._exhausted
    assert len(feeder._buffer) == 0


@pytest.mark.asyncio
async def test_get_next_score_stops_after_exhaustion(
    file_game_feeder: FileGameFeeder,
) -> None:
    feeder = file_game_feeder
    async for _ in feeder.get_next_score():
        pass

    with pytest.raises(StopAsyncIteration):
        await feeder.get_next_score().__anext__()

    assert feeder._exhausted
    assert len(feeder._buffer) == 0


@pytest.mark.asyncio
async def test_load_batch_file_not_found(
    tmp_path: Path, dummy_logger: logging.Logger, valid_config: ConfigParser
) -> None:
    game_dir = tmp_path / "data" / "games"
    game_dir.mkdir(parents=True, exist_ok=True)

    storage = FileStorage(valid_config, dummy_logger)
    missing_game_id = "game_not_found_404"
    feeder = FileGameFeeder(
        game_id=missing_game_id, storage=storage, logger=dummy_logger
    )

    assert not feeder.file_path.exists()

    with pytest.raises(FileNotFoundError):
        await feeder.get_next_score().__anext__()

    assert feeder._exhausted
    assert len(feeder._buffer) == 0


@pytest.mark.asyncio
async def test_cleanup_clears_buffer(file_game_feeder: FileGameFeeder) -> None:
    feeder = file_game_feeder
    await feeder.get_next_score().__anext__()  # Triggers loading
    assert len(feeder._buffer) > 0

    await feeder.cleanup()
    assert len(feeder._buffer) == 0
