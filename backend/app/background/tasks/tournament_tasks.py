import json
from typing import cast
from uuid import uuid4

from celery import current_app, shared_task
from celery.app.base import Celery

from app.config.tournament_builder import build_current_tournament_config
from app.domain.tournament.tennis import Tournament
from app.infra.keys import mens_tennis_lock, tournament_state
from app.infra.sync_redis import get_redis_client
from utils.logger import get_logger

logger = get_logger(__name__)
celery_app: Celery = cast(Celery, current_app._get_current_object())


@shared_task(bind=True, name="start_tennis_tournament")
def start_tennis_tournament(self):
    """Start the tournament that is currently active on the ATP calendar."""
    redis = get_redis_client()

    if not redis.setnx(mens_tennis_lock(), "locked"):
        logger.info("Tournament already running")
        return

    try:
        config = build_current_tournament_config()
        tournament_id = str(uuid4())
        tournament = Tournament(
            tournament_id=tournament_id,
            config=config,
        )

        redis.set(
            tournament_state(tournament_id),
            json.dumps(tournament.serialize()),
        )

        celery_app.send_task("run_games", args=[tournament_id])
        logger.info(
            "Tournament '%s' started (%s, %d players)",
            config["name"],
            config["level"],
            len(config["players"]),
        )
    except ValueError as e:
        redis.delete(mens_tennis_lock())
        logger.warning("No active tournament: %s", e)
    except Exception as e:
        redis.delete(mens_tennis_lock())
        logger.error("Failed to start tournament: %s", e)
        raise e


# Backwards compat alias
@shared_task(bind=True, name="start_mens_tennis_tournament")
def start_mens_tennis_tournament(self):
    start_tennis_tournament()
