from datetime import date

import pytest

from app.config.tournament_builder import (
    _effective_draw_size,
    _rounds_for_draw,
    _rule_set_for_category,
    build_tournament_config,
    find_current_tournament,
)

# ── Helpers ─────────────────────────────────────────────────────────────


class TestRuleSetForCategory:
    def test_grand_slam(self) -> None:
        assert _rule_set_for_category("Grand Slam") == "grandslam"

    def test_atp_finals(self) -> None:
        assert _rule_set_for_category("ATP Finals") == "grandslam"

    def test_atp_250(self) -> None:
        assert _rule_set_for_category("ATP 250") == "standard"

    def test_atp_500(self) -> None:
        assert _rule_set_for_category("ATP 500") == "standard"

    def test_atp_masters_1000(self) -> None:
        assert _rule_set_for_category("ATP Masters 1000") == "standard"

    def test_unknown_category(self) -> None:
        assert _rule_set_for_category("Something Else") == "standard"


class TestEffectiveDrawSize:
    def test_exact_match(self) -> None:
        assert _effective_draw_size(32) == 32

    def test_falls_down_to_nearest(self) -> None:
        assert _effective_draw_size(48) == 32

    def test_minimum(self) -> None:
        # 2 is now an exact match (Final only)
        assert _effective_draw_size(2) == 2

    def test_large_draw(self) -> None:
        assert _effective_draw_size(128) == 128


class TestRoundsForDraw:
    def test_128_draw_has_seven_rounds(self) -> None:
        rounds = _rounds_for_draw(128)
        assert len(rounds) == 7
        assert rounds[0]["code"] == "R128"
        assert rounds[-1]["code"] == "F"

    def test_32_draw_has_four_rounds(self) -> None:
        rounds = _rounds_for_draw(32)
        assert len(rounds) == 4
        assert rounds[0]["code"] == "R16"
        assert rounds[-1]["code"] == "F"

    def test_16_draw(self) -> None:
        rounds = _rounds_for_draw(16)
        assert len(rounds) == 4
        assert rounds[0]["code"] == "R16"

    def test_8_draw(self) -> None:
        rounds = _rounds_for_draw(8)
        assert len(rounds) == 3
        assert rounds[0]["code"] == "QF"


# ── Calendar lookup ─────────────────────────────────────────────────────


class TestFindCurrentTournament:
    def test_finds_australian_open(self) -> None:
        event = find_current_tournament(date(2026, 1, 25))
        assert event is not None
        assert event["tournament_name"] == "Australian Open"

    def test_finds_wimbledon(self) -> None:
        event = find_current_tournament(date(2026, 7, 5))
        assert event is not None
        assert event["tournament_name"] == "Wimbledon"

    def test_returns_none_when_no_event(self) -> None:
        # A date between tournaments
        event = find_current_tournament(date(2026, 12, 25))
        assert event is None

    def test_boundary_start_date(self) -> None:
        # Jan 18 is start of Australian Open; Adelaide ends Jan 18
        # Calendar may match either — just assert something is found
        event = find_current_tournament(date(2026, 1, 18))
        assert event is not None

    def test_boundary_end_date(self) -> None:
        event = find_current_tournament(date(2026, 1, 31))
        assert event is not None
        assert event["tournament_name"] == "Australian Open"


# ── Config building ─────────────────────────────────────────────────────


class TestBuildTournamentConfig:
    @pytest.fixture
    def sample_players(self):
        return [
            {"name": "Alcaraz", "world_ranking": 1, "country": "ESP"},
            {"name": "Sinner", "world_ranking": 2, "country": "ITA"},
            {"name": "Zverev", "world_ranking": 3, "country": "GER"},
            {"name": "Djokovic", "world_ranking": 4, "country": "SRB"},
            {"name": "Medvedev", "world_ranking": 5, "country": "RUS"},
            {"name": "Rublev", "world_ranking": 6, "country": "RUS"},
            {"name": "Ruud", "world_ranking": 7, "country": "NOR"},
            {"name": "De Minaur", "world_ranking": 8, "country": "AUS"},
        ]

    def test_basic_structure(self, sample_players) -> None:
        event = {
            "tournament_name": "Test Open",
            "category": "ATP 250",
            "surface": "Hard",
            "draws": 8,
            "start_date": "2026-01-01",
            "end_date": "2026-01-08",
        }
        config = build_tournament_config(event, sample_players)

        assert config["name"] == "Test Open"
        assert config["level"] == "ATP 250"
        assert config["surface"] == "Hard"
        assert config["game_defaults"]["rule_set"] == "standard"
        assert config["game_defaults"]["game_type"] == "tennis"

    def test_grand_slam_uses_grandslam_rules(self, sample_players) -> None:
        event = {
            "tournament_name": "Test Slam",
            "category": "Grand Slam",
            "surface": "Clay",
            "draws": 8,
            "start_date": "2026-01-01",
            "end_date": "2026-01-08",
        }
        config = build_tournament_config(event, sample_players)
        assert config["game_defaults"]["rule_set"] == "grandslam"

    def test_players_are_seeded(self, sample_players) -> None:
        event = {
            "tournament_name": "Test",
            "category": "ATP 250",
            "surface": "Hard",
            "draws": 8,
            "start_date": "2026-01-01",
            "end_date": "2026-01-08",
        }
        config = build_tournament_config(event, sample_players)

        # Seed 1 should be at position 0
        assert config["players"][0] == "Alcaraz"
        # Seed 2 should be at last position
        assert config["players"][7] == "Sinner"

    def test_player_metadata_included(self, sample_players) -> None:
        event = {
            "tournament_name": "Test",
            "category": "ATP 250",
            "surface": "Hard",
            "draws": 8,
            "start_date": "2026-01-01",
            "end_date": "2026-01-08",
        }
        config = build_tournament_config(event, sample_players)

        meta = config["player_metadata"]
        assert meta["Alcaraz"]["world_ranking"] == 1
        assert meta["Sinner"]["world_ranking"] == 2

    def test_draws_string_parsed(self, sample_players) -> None:
        event = {
            "tournament_name": "Test",
            "category": "Teams",
            "surface": "Hard",
            "draws": "18 teams",
            "start_date": "2026-01-01",
            "end_date": "2026-01-08",
        }
        config = build_tournament_config(event, sample_players)
        assert len(config["players"]) == 8  # capped at available players

    def test_fewer_players_than_draw(self) -> None:
        """When fewer players than draw size, use what's available."""
        players = [
            {"name": "Alcaraz", "world_ranking": 1},
            {"name": "Sinner", "world_ranking": 2},
            {"name": "Zverev", "world_ranking": 3},
            {"name": "Djokovic", "world_ranking": 4},
        ]
        event = {
            "tournament_name": "Small",
            "category": "ATP 250",
            "surface": "Hard",
            "draws": 32,
            "start_date": "2026-01-01",
            "end_date": "2026-01-08",
        }
        config = build_tournament_config(event, players)
        assert len(config["players"]) == 4
        # 4-player draw → SF and F
        assert len(config["rounds"]) == 2
        assert config["rounds"][0]["code"] == "SF"
