import json
from typing import Any

import redis.asyncio as redis

from utils.logger import get_logger


async def fetch_live_games(
    redis_client: redis.Redis,
    *,
    limit: int,
    key_pattern: str,
    visible_states: set[str],
    scan_batch_size: int,
) -> list[dict[str, Any]]:
    logger = get_logger()
    results: list[dict[str, Any]] = []
    cursor = 0

    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor,
            match=key_pattern,
            count=scan_batch_size,
        )

        logger.debug(f"Fetching live games...: {keys}")
        if keys:
            values = await redis_client.mget(*keys)
            logger.debug(f"Fetched live games...: {values}")

            for raw in values:
                if not raw:
                    continue

                try:
                    data = json.loads(raw)
                    # logger.debug(f"Parsed live games...: {data}")
                except json.JSONDecodeError:
                    logger.debug("Failed to parse live games...")
                    continue

                if data.get("game_state") not in visible_states:
                    logger.debug("Skipping non-visible game...")
                    continue

                results.append(data)

                if len(results) >= limit:
                    return results

        if cursor == 0:
            break

    logger.debug(f"Fetched live games...: {results}")
    return results
