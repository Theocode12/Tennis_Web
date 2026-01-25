AUSTRALIAN_OPEN_MENS_CONFIG = {
    "name": "Australian Open",
    "season": 2026,
    "surface": "Hard",
    "level": "Grand Slam",
    # Tournament structure
    "rounds": [
        {"code": "R16", "name": "Round of 16", "required_players": 16},
        {"code": "QF", "name": "Quarter Final", "required_players": 8},
        {"code": "SF", "name": "Semi Final", "required_players": 4},
        {"code": "F", "name": "Final", "required_players": 2},
    ],
    # Game defaults (reused for every match)
    "game_defaults": {
        "game_type": "tennis",
        "rule_set": "standard",
        "play_mode": "multiplayer",
        "match_format": "singles",
    },
    # Creator metadata
    "created_by": {
        "type": "SYSTEM",
        "identifier": "tournament-engine",
        "display_name": "Tournament Engine",
    },
    # Initial players
    "players": [
        "Federer R.",
        "Medvedev D.",
        "Tsitsipas S.",
        "Sampras P.",
        "Agassi A.",
        "Borg B.",
        "Djokovic N.",
        "McEnroe J.",
        "Murray A.",
        "Alcaraz C.",
        "Sinner J.",
        "Zverev A.",
        "Rublev A.",
        "Thiem D.",
        "Nadal R.",
        "Lendl I.",
    ],
}
