import json
import pytest
from unittest.mock import MagicMock, patch, ANY
from app.background.tasks.tournament_tasks import start_mens_tennis_tournament

@patch("app.background.tasks.tournament_tasks.get_redis_client")
@patch("app.background.tasks.tournament_tasks.Tournament")
@patch("app.background.tasks.tournament_tasks.celery_app.send_task")
def test_start_mens_tennis_tournament_success(
    mock_send_task, mock_tournament_cls, mock_get_redis
):
    # Setup
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.setnx.return_value = True  # Lock acquired
    
    mock_tournament = MagicMock()
    mock_tournament_cls.return_value = mock_tournament
    mock_tournament.serialize.return_value = {"state": "data"}
    
    # .run() for bound task already has 'self'
    start_mens_tennis_tournament.run()
    
    # Verify
    mock_redis.setnx.assert_called_once_with("tournament:tennis:mens:lock", "locked")
    mock_tournament_cls.assert_called_once()
    
    # Verify state persistence
    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert args[0].startswith("tournament:")
    assert args[0].endswith(":state")
    assert json.loads(args[1]) == {"state": "data"}
    
    # Verify next task triggered
    mock_send_task.assert_called_once_with("run_games", args=[ANY])

@patch("app.background.tasks.tournament_tasks.get_redis_client")
def test_start_mens_tennis_tournament_locked(mock_get_redis):
    # Setup
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.setnx.return_value = False  # Lock NOT acquired
    
    # Execute
    start_mens_tennis_tournament.run()
    
    # Verify
    mock_redis.setnx.assert_called_once_with("tournament:tennis:mens:lock", "locked")
    # Should exit early
    mock_redis.set.assert_not_called()

@patch("app.background.tasks.tournament_tasks.get_redis_client")
@patch("app.background.tasks.tournament_tasks.Tournament")
def test_start_mens_tennis_tournament_failure_releases_lock(
    mock_tournament_cls, mock_get_redis
):
    # Setup
    mock_redis = MagicMock()
    mock_get_redis.return_value = mock_redis
    mock_redis.setnx.return_value = True  # Lock acquired
    
    mock_tournament_cls.side_effect = ValueError("Error starting")
    
    # Execute & Verify
    with pytest.raises(ValueError):
        start_mens_tennis_tournament.run()
    
    # Verify lock released
    mock_redis.delete.assert_called_once_with("tournament:tennis:mens:lock")
