import json
from typing import cast

from celery import shared_task

from app.domain.tournament.tennis import Tournament, TournamentResult
from app.infra.keys import mens_tennis_lock, tournament_active_matches, tournament_state
from app.infra.sync_redis import get_redis_client
from utils.load_config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, name="run_games")
def run_tournament_games_task(self, tournament_id: str):
    redis = get_redis_client()
    config = load_config()

    try:
        raw_state = redis.get(tournament_state(tournament_id))
        if not raw_state:
            logger.warning("No state found for tournament %s", tournament_id)
            raise ValueError(f"No state found for tournament {tournament_id}")

        tournament = Tournament.from_state(json.loads(cast(str, raw_state)))
        result, match_ids = tournament.tick()

        if result in (TournamentResult.FINISHED, TournamentResult.NO_MATCHES):
            redis.delete(tournament_state(tournament_id))
            redis.delete(mens_tennis_lock())

            redis.xadd(
                config["background"]["StreamKey"],
                {
                    "type": "TOURNAMENT_FINISHED",
                    "tournament_id": tournament_id,
                    "source": "tournament_engine",
                },
                maxlen=config.getint(
                    "background",
                    "StreamMaxLength",
                    fallback=1000,
                ),
            )

            logger.info(
                "Tournament %s finalized (%s)",
                tournament_id,
                result,
            )

            return

        if match_ids:
            logger.info("Adding %s matches to active set", len(match_ids))
            key = tournament_active_matches(tournament_id)
            ex = config.getint("background", "TournamentStateTTL", fallback=43200)
            redis.sadd(key, *match_ids)
            redis.expire(key, ex)

        for match_id in match_ids:
            redis.xadd(
                config["background"]["StreamKey"],
                {
                    "type": "START_STREAM",
                    "match_id": match_id,
                    "tournament_id": tournament_id,
                    "source": "tournament_engine",
                },
                maxlen=config.getint("background", "StreamMaxLength", fallback=1000),
            )

        redis.set(
            tournament_state(tournament_id),
            json.dumps(tournament.serialize()),
            ex=config.getint("background", "TournamentStateTTL", fallback=43200),
        )

    except Exception as e:
        redis.delete(mens_tennis_lock())
        logger.error("Error in tournament task: %s", e)
        raise e
