import json
from typing import cast
from uuid import uuid4

from celery import current_app, shared_task
from celery.app.base import Celery

from app.config.competitions.aus_open.mens import AUSTRALIAN_OPEN_MENS_CONFIG
from app.domain.tournament.tennis import Tournament
from app.infra.keys import mens_tennis_lock, tournament_state
from app.infra.sync_redis import get_redis_client
from utils.logger import get_logger

logger = get_logger(__name__)
celery_app: Celery = cast(Celery, current_app._get_current_object())


@shared_task(bind=True, name="start_mens_tennis_tournament")
def start_mens_tennis_tournament(self):
    redis = get_redis_client()

    if not redis.setnx(mens_tennis_lock(), "locked"):
        logger.info("Men's tournament already running")
        return

    try:
        tournament_id = str(uuid4())
        tournament = Tournament(
            tournament_id=tournament_id,
            config=AUSTRALIAN_OPEN_MENS_CONFIG,
        )

        redis.set(
            tournament_state(tournament_id),
            json.dumps(tournament.serialize()),
        )

        celery_app.send_task("run_games", args=[tournament_id])
        logger.info("Men's tournament %s started", tournament_id)
    except Exception as e:
        redis.delete(mens_tennis_lock())
        logger.error("Failed to start men's tournament: %s", e)
        raise e
