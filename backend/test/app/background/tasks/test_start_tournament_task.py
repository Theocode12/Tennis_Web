from unittest.mock import ANY, MagicMock, patch

import pytest

from app.background.tasks.tournament_tasks import start_tennis_tournament

TEST_CONFIG = {
    "name": "Test Open",
    "level": "ATP 250",
    "players": ["p1", "p2"],
    "rounds": [{"code": "F", "name": "Final", "required_players": 2}],
    "game_defaults": {},
    "created_by": {"type": "SYSTEM", "identifier": "test"},
}


@patch("app.background.tasks.tournament_tasks.get_redis_client")
@patch("app.background.tasks.tournament_tasks.Tournament")
@patch("app.background.tasks.tournament_tasks.build_current_tournament_config")
@patch("app.background.tasks.tournament_tasks.celery_app.send_task")
def test_start_tennis_tournament_success(
    mock_send_task,
    mock_build_config,
    mock_tournament_cls,
    mock_get_redis,
):
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.setnx.return_value = True

    mock_build_config.return_value = TEST_CONFIG

    mock_tournament = MagicMock()
    mock_tournament_cls.return_value = mock_tournament
    mock_tournament.serialize.return_value = {"state": "data"}

    start_tennis_tournament.run()

    mock_redis.setnx.assert_called_once_with("tournament:tennis:mens:lock", "locked")
    mock_build_config.assert_called_once()
    mock_tournament_cls.assert_called_once_with(
        tournament_id=ANY,
        config=TEST_CONFIG,
    )

    # Verify state persisted
    mock_redis.set.assert_called_once()
    args, _ = mock_redis.set.call_args
    assert args[0].startswith("tournament:")
    assert args[0].endswith(":state")

    # Verify next task dispatched
    mock_send_task.assert_called_once_with("run_games", args=[ANY])


@patch("app.background.tasks.tournament_tasks.get_redis_client")
def test_start_tennis_tournament_locked(mock_get_redis):
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.setnx.return_value = False

    start_tennis_tournament.run()

    mock_redis.setnx.assert_called_once()
    mock_redis.set.assert_not_called()


@patch("app.background.tasks.tournament_tasks.get_redis_client")
@patch("app.background.tasks.tournament_tasks.build_current_tournament_config")
def test_start_tennis_tournament_no_active_event(mock_build_config, mock_get_redis):
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.setnx.return_value = True

    mock_build_config.side_effect = ValueError("No active tournament")

    # Should not raise — just logs warning and releases lock
    start_tennis_tournament.run()

    mock_redis.delete.assert_called_once_with("tournament:tennis:mens:lock")


@patch("app.background.tasks.tournament_tasks.get_redis_client")
@patch("app.background.tasks.tournament_tasks.build_current_tournament_config")
def test_start_tennis_tournament_failure_releases_lock(mock_build_config, mock_get_redis):
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.setnx.return_value = True

    mock_build_config.side_effect = RuntimeError("Unexpected error")

    with pytest.raises(RuntimeError):
        start_tennis_tournament.run()

    mock_redis.delete.assert_called_once_with("tournament:tennis:mens:lock")
