import json
from unittest.mock import MagicMock, patch

import pytest

from app.background.tasks.game_tasks import run_tournament_games_task

# Define a standard valid state for testing
VALID_STATE = {
    "id": "tournament-123",
    "config": {
        "name": "US Open",
        "players": ["p1", "p2"],
        "rounds": [{"code": "F", "name": "Final", "required_players": 2}],
        "game_defaults": {},
    },
    "current_round_index": 0,
    "active_players": ["p1", "p2"],
    "completed_matches": [],
    "match_players": {},
    "is_finished": False,
    "winner": None,
}


@patch("app.background.tasks.game_tasks.get_redis_client")
@patch("app.background.tasks.game_tasks.load_config")
@patch("app.background.tasks.game_tasks.Tournament.from_state")
def test_run_games_success(mock_from_state, mock_load_config, mock_get_redis):
    # Setup
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.get.return_value = json.dumps(VALID_STATE).encode()

    mock_config = MagicMock()
    mock_config.__getitem__.side_effect = lambda k: {"background": {"StreamKey": "tournament:commands"}}[k]
    mock_config.getint.return_value = 120
    mock_load_config.return_value = mock_config

    mock_tournament = MagicMock()
    mock_from_state.return_value = mock_tournament
    
    # tick() returns (result, match_ids)
    from app.domain.tournament.tennis import TournamentResult
    mock_tournament.tick.return_value = (TournamentResult.CONTINUE, ["match-1", "match-2"])
    mock_tournament.serialize.return_value = {"state": "updated"}

    # Mock apply_async on the task instance
    with patch.object(run_tournament_games_task, "apply_async") as mock_apply_async:
        run_tournament_games_task.run("tournament-123")

        # Verify
        mock_redis.get.assert_called_once_with("tournament:tournament-123:state")
        mock_tournament.tick.assert_called_once()

        # Verify Redis commands sent
        assert mock_redis.xadd.call_count == 2
        mock_redis.xadd.assert_any_call(
            "tournament:commands", {"type": "START_STREAM", "match_id": "match-1"}
        )

        # Verify rescheduled
        mock_apply_async.assert_called_once()


@patch("app.background.tasks.game_tasks.get_redis_client")
@patch("app.background.tasks.game_tasks.load_config")
@patch("app.background.tasks.game_tasks.Tournament.from_state")
def test_run_games_finishes(mock_from_state, mock_load_config, mock_get_redis):
    # Setup
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.get.return_value = json.dumps(VALID_STATE).encode()

    mock_tournament = MagicMock()
    mock_from_state.return_value = mock_tournament
    
    from app.domain.tournament.tennis import TournamentResult
    mock_tournament.tick.return_value = (TournamentResult.FINISHED, [])

    # Execute
    run_tournament_games_task.run("tournament-123")

    # Verify keys deleted
    mock_redis.delete.assert_any_call("tournament:tournament-123:state")
    mock_redis.delete.assert_any_call("tournament:tennis:mens:lock")


@patch("app.background.tasks.game_tasks.get_redis_client")
def test_run_games_not_found(mock_get_redis):
    # Setup
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.get.return_value = None  # State missing

    # Execute - should raise ValueError
    with pytest.raises(ValueError, match="No state found for tournament"):
        run_tournament_games_task.run("tournament-123")

    # Verify set was not called
    mock_redis.set.assert_not_called()


@patch("app.background.tasks.game_tasks.get_redis_client")
@patch("app.background.tasks.game_tasks.load_config")
@patch("app.background.tasks.game_tasks.Tournament.from_state")
def test_run_games_failure_releases_lock(mock_from_state, mock_load_config, mock_get_redis):
    # Setup
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.get.side_effect = ValueError("Redis explosion")

    # Execute
    with pytest.raises(ValueError):
        run_tournament_games_task.run("tournament-123")

    # Verify lock released
    mock_redis.delete.assert_called_once_with("tournament:tennis:mens:lock")
