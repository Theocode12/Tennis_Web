from configparser import ConfigParser
from typing import Annotated

import redis.asyncio as redis
from fastapi import APIRouter, Depends

from app.dependencies import get_app_config, get_redis_client
from app.services.live_games import fetch_live_games

router = APIRouter()


@router.get("/live-games")
async def get_live_games(
    redis_client: Annotated[redis.Redis, Depends(get_redis_client)],
    config: Annotated[ConfigParser, Depends(get_app_config)],
    limit: int = 5,
):
    key_pattern = config.get(
        "liveGameRegistry", "redisKeyPattern", fallback="live:game:*"
    )

    scan_batch_size = config.getint("liveGameRegistry", "scanBatchSize", fallback=20)

    visible_states = {
        s.strip()
        for s in config.get(
            "liveGameRegistry", "visibleStates", fallback="ongoing"
        ).split(",")
    }

    games = await fetch_live_games(
        redis_client,
        limit=limit,
        key_pattern=key_pattern,
        visible_states=visible_states,
        scan_batch_size=scan_batch_size,
    )

    return {
        "total": len(games),
        "data": games,
    }
