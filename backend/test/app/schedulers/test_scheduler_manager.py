from __future__ import annotations

import asyncio
import logging
from configparser import ConfigParser
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from app.scheduler.manager import SchedulerManager


# Dummy GameScheduler and Feeder
class DummyFeeder:
    async def get_metadata(self) -> dict[str, bool]:
        return {"metadata": True}


class DummyScheduler:
    def __init__(self, game_id: str, broker: MagicMock, feeder: DummyFeeder) -> None:
        self.game_id = game_id
        self.broker = broker
        self.feeder = feeder
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        print(f"Scheduler for {self.game_id} started.")
        await self._stop_event.wait()
        print(f"Scheduler for {self.game_id} stopped.")

    def stop(self) -> None:
        print("stop is called")
        self._stop_event.set()

    async def get_metadata(self) -> dict[str, bool]:
        return {"metadata": True}


@pytest.fixture
def broker() -> MagicMock:
    return MagicMock()


@pytest.fixture
def scheduler_manager(
    broker: MagicMock, valid_config: ConfigParser, dummy_logger: logging.Logger
) -> SchedulerManager:
    return SchedulerManager(broker, config=valid_config, logger=dummy_logger)


@pytest.mark.asyncio
async def test_shutdown_all(
    monkeypatch: MonkeyPatch, scheduler_manager: SchedulerManager
) -> None:
    monkeypatch.setattr(
        "app.scheduler.manager.create_game_feeder", lambda *a, **kw: DummyFeeder()
    )
    monkeypatch.setattr("app.scheduler.manager.GameScheduler", DummyScheduler)

    await scheduler_manager.create_or_get_scheduler("game-a")
    await scheduler_manager.create_or_get_scheduler("game-b")

    await scheduler_manager.shutdown()

    assert scheduler_manager._schedulers == {}
    assert scheduler_manager._scheduler_tasks == {}


@pytest.mark.asyncio
async def test_create_and_get_scheduler(
    monkeypatch: MonkeyPatch,
    scheduler_manager: SchedulerManager,
) -> None:
    monkeypatch.setattr(
        "app.scheduler.manager.create_game_feeder", lambda *a, **kw: DummyFeeder()
    )
    monkeypatch.setattr("app.scheduler.manager.GameScheduler", DummyScheduler)

    game_id = "game-1"
    scheduler, task = await scheduler_manager.create_or_get_scheduler(game_id)

    assert scheduler_manager.has_scheduler(game_id)
    assert scheduler_manager.get_scheduler(game_id) is scheduler
    assert isinstance(task, asyncio.Task)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_scheduler_reuse(
    monkeypatch: MonkeyPatch, scheduler_manager: SchedulerManager
) -> None:
    monkeypatch.setattr(
        "app.scheduler.manager.create_game_feeder", lambda *a, **kw: DummyFeeder()
    )
    monkeypatch.setattr("app.scheduler.manager.GameScheduler", DummyScheduler)

    game_id = "game-2"
    sched1, task1 = await scheduler_manager.create_or_get_scheduler(game_id)
    sched2, task2 = await scheduler_manager.create_or_get_scheduler(game_id)

    assert sched1 is sched2
    assert task1 is task2

    task1.cancel()

    try:
        await task1
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_get_game_data(
    monkeypatch: MonkeyPatch, scheduler_manager: SchedulerManager
) -> None:
    monkeypatch.setattr(
        "app.scheduler.manager.create_game_feeder", lambda *a, **kw: DummyFeeder()
    )
    monkeypatch.setattr("app.scheduler.manager.GameScheduler", DummyScheduler)

    game_id = "game-3"
    await scheduler_manager.create_or_get_scheduler(game_id)

    metadata = await scheduler_manager.get_game_data(game_id)
    assert metadata == {"metadata": True}


@pytest.mark.asyncio
async def test_cleanup_scheduler(
    monkeypatch: MonkeyPatch, scheduler_manager: SchedulerManager
) -> None:
    monkeypatch.setattr(
        "app.scheduler.manager.create_game_feeder", lambda *a, **kw: DummyFeeder()
    )
    monkeypatch.setattr("app.scheduler.manager.GameScheduler", DummyScheduler)

    game_id = "game-4"
    scheduler, task = await scheduler_manager.create_or_get_scheduler(game_id)

    assert scheduler_manager.has_scheduler(game_id)

    scheduler.stop()  # type: ignore

    await asyncio.sleep(0.05)  # Yield control to let task finish and cleanup trigger

    await task
    assert task.done()

    if scheduler_manager._background_tasks:
        await scheduler_manager._background_tasks.pop()

    assert not scheduler_manager.has_scheduler(game_id)
