from __future__ import annotations

from typing import Any


def seed_positions(draw_size: int) -> list[int]:
    """
    Return the bracket positions for seeds 1..draw_size.

    The recursive algorithm places the top seed at position 0, the
    second seed at the far end, then interleaves the remaining seeds
    into sub-quarters of the bracket.  This guarantees that seed 1
    and seed 2 can only meet in the final.

    >>> seed_positions(4)
    [0, 3, 1, 2]
    >>> seed_positions(8)
    [0, 7, 3, 4, 1, 6, 2, 5]
    """
    if draw_size == 1:
        return [0]
    half = seed_positions(draw_size // 2)
    result: list[int] = []
    for h in half:
        result.append(h)
        result.append(draw_size - 1 - h)
    return result


def apply_seeding(players: list[dict[str, Any]], draw_size: int) -> list[dict[str, Any]]:
    """
    Arrange *players* (sorted by world_ranking ascending) into
    bracket order using proper tournament seeding.

    Only the top *draw_size* players are used.  Remaining slots are
    left for qualifying / wildcards (not yet implemented).
    """
    seeded = sorted(players, key=lambda p: p["world_ranking"])[:draw_size]
    positions = seed_positions(draw_size)

    bracket: list[dict[str, Any]] = [{} for _ in range(draw_size)]
    for seed_index, player in enumerate(seeded):
        bracket[positions[seed_index]] = player

    return bracket
