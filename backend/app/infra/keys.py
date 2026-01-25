def tournament_state(tournament_id: str) -> str:
    return f"tournament:{tournament_id}:state"


def mens_tennis_lock() -> str:
    return "tournament:tennis:mens:lock"
