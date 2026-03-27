from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from app.config.seeding import apply_seeding

# Paths

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_CALENDAR_PATH = _BACKEND_DIR / "db" / "data" / "atp-calender.json"
_PLAYERS_PATH = _BACKEND_DIR / "db" / "data" / "players.json"

# Category → rule_set mapping

_CATEGORY_RULESET: dict[str, str] = {
    "Grand Slam": "grandslam",
    "ATP Finals": "grandslam",
}

# Draw size → round specs

_ROUND_TEMPLATES: dict[int, list[dict[str, Any]]] = {
    128: [
        {"code": "R128", "name": "Round of 128", "required_players": 128},
        {"code": "R64", "name": "Round of 64", "required_players": 64},
        {"code": "R32", "name": "Round of 32", "required_players": 32},
        {"code": "R16", "name": "Round of 16", "required_players": 16},
        {"code": "QF", "name": "Quarter Final", "required_players": 8},
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    96: [
        {"code": "R64", "name": "Round of 64", "required_players": 64},
        {"code": "R32", "name": "Round of 32", "required_players": 32},
        {"code": "R16", "name": "Round of 16", "required_players": 16},
        {"code": "QF", "name": "Quarter Final", "required_players": 8},
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    64: [
        {"code": "R64", "name": "Round of 64", "required_players": 64},
        {"code": "R32", "name": "Round of 32", "required_players": 32},
        {"code": "R16", "name": "Round of 16", "required_players": 16},
        {"code": "QF", "name": "Quarter Final", "required_players": 8},
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    56: [
        {"code": "R32", "name": "Round of 32", "required_players": 32},
        {"code": "R16", "name": "Round of 16", "required_players": 16},
        {"code": "QF", "name": "Quarter Final", "required_players": 8},
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    32: [
        {"code": "R16", "name": "Round of 16", "required_players": 16},
        {"code": "QF", "name": "Quarter Final", "required_players": 8},
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    28: [
        {"code": "R16", "name": "Round of 16", "required_players": 16},
        {"code": "QF", "name": "Quarter Final", "required_players": 8},
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    16: [
        {"code": "R16", "name": "Round of 16", "required_players": 16},
        {"code": "QF", "name": "Quarter Final", "required_players": 8},
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    8: [
        {"code": "QF", "name": "Quarter Final", "required_players": 8},
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    4: [
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    2: [
        {"code": "F", "name": "Final", "required_players": 2},
    ],
}


# Helpers


def _load_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


def _effective_draw_size(raw: int) -> int:
    """Map a draw size to the nearest supported template key."""
    if raw in _ROUND_TEMPLATES:
        return raw
    # Fall back to the largest template that fits
    for key in sorted(_ROUND_TEMPLATES, reverse=True):
        if raw >= key:
            return key
    return 8  # minimum


def _rounds_for_draw(draw_size: int) -> list[dict[str, Any]]:
    effective = _effective_draw_size(draw_size)
    return _ROUND_TEMPLATES[effective]


def _rule_set_for_category(category: str) -> str:
    return _CATEGORY_RULESET.get(category, "standard")


# Public API


def find_current_tournament(ref_date: date | None = None) -> dict[str, Any] | None:
    """
    Return the ATP calendar event whose date range contains *ref_date*
    (defaults to today).  Returns ``None`` when no event is active.
    """
    today = ref_date or date.today()
    calendar = _load_json(_CALENDAR_PATH)

    for event in calendar["events"]:
        start = date.fromisoformat(event["start_date"])
        end = date.fromisoformat(event["end_date"])
        if start <= today <= end:
            return event
    return None


def load_players() -> list[dict[str, Any]]:
    return _load_json(_PLAYERS_PATH)


def build_tournament_config(
    event: dict[str, Any],
    players: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build a full tournament config dict from an ATP calendar event.

    If *players* is ``None`` the default player pool is loaded from
    ``data/players.json``.
    """
    if players is None:
        players = load_players()

    draw_size = event.get("draws", 32)
    if isinstance(draw_size, str):
        draw_size = int(draw_size.split()[0])  # "18 teams" → 18

    # Cap draw size to available players
    actual_draw = min(draw_size, len(players))

    rounds = _rounds_for_draw(actual_draw)
    first_round_size = rounds[0]["required_players"]

    # Seed the top-ranked players into bracket order
    bracket = apply_seeding(players, first_round_size)

    return {
        "name": event["tournament_name"],
        "season": 2026,
        "surface": event.get("surface", "Hard"),
        "level": event.get("category", "ATP 250"),
        "rounds": rounds,
        "game_defaults": {
            "game_type": "tennis",
            "rule_set": _rule_set_for_category(event.get("category", "")),
            "play_mode": "multiplayer",
            "match_format": "singles",
        },
        "created_by": {
            "type": "SYSTEM",
            "identifier": "tournament-engine",
            "display_name": "Tournament Engine",
        },
        "players": [p["name"] for p in bracket],
        "player_metadata": {p["name"]: p for p in bracket},
    }


def build_current_tournament_config(
    ref_date: date | None = None,
    players: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Convenience wrapper: find the current tournament and build its config.

    Raises ``ValueError`` if no tournament is active.
    """
    event = find_current_tournament(ref_date)
    if event is None:
        raise ValueError(f"No active tournament found for date {ref_date or date.today()}")
    return build_tournament_config(event, players)
