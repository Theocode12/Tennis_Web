import pytest
import asyncio
import uuid
from collections import deque
from unittest.mock import MagicMock, AsyncMock, patch
from app.domain.tournament.tennis import Tournament, RoundSpec
from app.config.competitions.us_open.mens import US_OPEN_MENS_CONFIG as TENNIS_TOURNAMENT_CONFIG

@pytest.fixture
def mock_dependencies():
    with patch("app.domain.tournament.tennis.get_logger") as mock_get_logger, \
         patch("app.domain.tournament.tennis.CONFIG", {"some": "config"}) as mock_config, \
         patch("app.domain.tournament.tennis.ConfigParser") as mock_config_parser, \
         patch("app.domain.tournament.tennis.GameBuilder") as mock_builder, \
         patch("app.domain.tournament.tennis.GameRunner") as mock_runner:
        
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Setup mock runner to return a winner when .run() is called
        runner_instance = AsyncMock()
        mock_runner.return_value = runner_instance
        
        yield {
            "logger": mock_logger,
            "builder": mock_builder,
            "runner": mock_runner,
            "runner_instance": runner_instance,
            "config_parser": mock_config_parser
        }

def test_initialization(mock_dependencies):
    tournament_id = "test-tournament"
    tournament = Tournament(tournament_id, TENNIS_TOURNAMENT_CONFIG)
    
    assert tournament.id == tournament_id
    assert len(tournament.rounds) == 4
    assert tournament.current_round_index == 0
    assert len(tournament.active_players) == 16
    assert isinstance(tournament.completed_matches, deque)
    assert tournament.is_finished is False
    assert tournament.winner is None

def test_validate_round_state(mock_dependencies):
    tournament = Tournament("test", TENNIS_TOURNAMENT_CONFIG)
    
    # Valid state
    tournament.validate_round_state()
    
    # Finished tournament
    tournament.is_finished = True
    with pytest.raises(ValueError, match="Tournament already finished"):
        tournament.validate_round_state()
    tournament.is_finished = False
    
    # Invalid player count
    tournament.active_players.pop()
    with pytest.raises(ValueError, match="Round R16 requires 16 players"):
        tournament.validate_round_state()

def test_build_match_payload(mock_dependencies):
    tournament = Tournament("test", TENNIS_TOURNAMENT_CONFIG)
    match_id = "match-123"
    pa, pb = "p1", "p2"
    
    payload = tournament._build_match_payload(match_id, pa, pb)
    
    assert payload["game_id"] == match_id
    assert payload["players"] == [["p1"], ["p2"]]
    assert payload["match_context"]["tournament"]["tournament_id"] == "test"
    assert payload["match_context"]["tournament"]["round"]["code"] == "R16"

@pytest.mark.asyncio
async def test_get_next_match_payloads_flow(mock_dependencies):
    deps = mock_dependencies
    tournament = Tournament("test", TENNIS_TOURNAMENT_CONFIG)
    
    # We want to control the winner for each match to ensure valid winners
    # The tournament creates 8 matches in R16
    # We'll use a side effect to return the first player as the winner
    
    winners = deque(TENNIS_TOURNAMENT_CONFIG["players"][::2])
    
    async def mock_run():
        winner = winners.popleft() if winners else "novak_djokovic"
        return ([], winner)
    
    deps["runner_instance"].run.side_effect = mock_run
    
    # 1. First poll: No matches queued, should run 8 matches and return first 4
    batch1 = await tournament.get_next_match_payloads()
    assert len(batch1) == 4
    assert len(tournament.completed_matches) == 4  # 8 ran, 4 remained in queue
    
    # 2. Second poll: Should return the remaining 4 matches from the queue
    batch2 = await tournament.get_next_match_payloads()
    assert len(batch2) == 4
    assert len(tournament.completed_matches) == 0
    
    # 3. Verify round advanced
    assert tournament.current_round_index == 1
    assert tournament.current_round.code == "QF"
    assert len(tournament.active_players) == 8

@pytest.mark.asyncio
async def test_record_match_result_errors(mock_dependencies):
    tournament = Tournament("test", TENNIS_TOURNAMENT_CONFIG)
    
    # Unknown match
    with pytest.raises(ValueError, match="Unknown match"):
        tournament._record_match_result("unknown", "p1")
        
    # Invalid winner
    match_id = "m1"
    tournament.match_players[match_id] = ("p1", "p2")
    with pytest.raises(ValueError, match="Invalid winner"):
        tournament._record_match_result(match_id, "p3")

def test_serialize_deserialize(mock_dependencies):
    tournament = Tournament("test", TENNIS_TOURNAMENT_CONFIG)
    tournament.completed_matches.append("m1")
    tournament.match_players["m2"] = ("p1", "p2")
    
    state = tournament.serialize()
    new_tournament = Tournament.from_state(state)
    
    assert new_tournament.id == tournament.id
    assert list(new_tournament.completed_matches) == ["m1"]
    assert new_tournament.match_players["m2"] == ["p1", "p2"] or new_tournament.match_players["m2"] == ("p1", "p2")
    assert new_tournament.current_round_index == 0

@pytest.mark.asyncio
async def test_full_tournament_progression(mock_dependencies):
    deps = mock_dependencies
    tournament = Tournament("test", TENNIS_TOURNAMENT_CONFIG)
    
    # We need to track which builder goes with which runner instance
    # But since we run in gather, it's easier to mock _run_match directly or 
    # make GameRunner.run look at its own builder.
    
    async def dynamic_run(runner_self):
        # The runner_self is the mock runner instance. 
        # We need to find the builder instance it was created with.
        # This is tricky with current mock structure.
        
        # Simpler: patch _run_match to return the first player in the match_players dict for that match_id
        return "winner_placeholder" # Not used if we patch _run_match

    # Let's patch _run_match to be more robust
    async def mock_run_match(match_id, runner):
        p1, p2 = tournament.match_players[match_id]
        await asyncio.sleep(0)
        return match_id, p1 # First player always wins
    
    with patch.object(Tournament, "_run_match", side_effect=mock_run_match):
        # R16 -> QF (16 players -> 8 matches)
        res = await tournament.get_next_match_payloads()
        assert len(res) == 4
        res = await tournament.get_next_match_payloads()
        assert len(res) == 4
        assert tournament.current_round_index == 1
        assert tournament.current_round.code == "QF"
        assert len(tournament.active_players) == 8
        
        # QF -> SF (8 players -> 4 matches)
        res = await tournament.get_next_match_payloads()
        assert len(res) == 4
        assert tournament.current_round.code == "SF"
        assert len(tournament.active_players) == 4
        
        # SF -> Final (4 players -> 2 matches)
        res = await tournament.get_next_match_payloads()
        assert len(res) == 2
        assert tournament.current_round.code == "F"
        assert len(tournament.active_players) == 2
        
        # Final -> winner (2 players -> 1 match)
        res = await tournament.get_next_match_payloads()
        assert len(res) == 1
        assert tournament.is_finished is True
        assert tournament.winner == "Federer R."
