from fastapi import FastAPI

from app.background.tasks.tournament_tasks import start_tennis_tournament
from app.celery import app as celery_app
from app.dependencies import get_redis_client
from app.infra.keys import tournament_active_matches
from app.scheduler.manager import SchedulerContext
from utils.logger import get_logger

logger = get_logger(__name__)


async def handle_command(
    app: FastAPI,
    message_id: str,
    payload: dict,
) -> None:
    command_type = payload.get("type")

    if command_type == "START_STREAM":
        await handle_start_stream(app, payload)
    elif command_type == "MATCH_FINISHED":
        await handle_match_finished(app, payload)
    elif command_type == "TOURNAMENT_FINISHED":
        await handle_tournament_finished(app, payload)
    else:
        logger.warning(f"Unknown command type: {payload}")


async def handle_start_stream(app: FastAPI, payload: dict) -> None:
    logger.info(f"Handling START_STREAM command with payload: {payload}")
    match_id = payload.get("match_id")
    tournament_id = payload.get("tournament_id")
    if not match_id:
        raise ValueError("Missing match_id")

    logger.info(f"START_STREAM received: {match_id}")

    sio_context = app.state.sio_context
    scheduler_manager = sio_context.get_scheduler_manager()

    context = SchedulerContext(
        game_id=str(match_id),
        tournament_id=str(tournament_id),
        source="tournament_engine",
    )

    scheduler, task = await scheduler_manager.create_or_get_scheduler(context)
    await scheduler.start()


async def handle_match_finished(
    app: FastAPI,
    payload: dict,
) -> None:
    """
    Handle MATCH_FINISHED events emitted by schedulers.

    Responsibilities:
    - remove completed match from tournament active set
    - detect round completion barrier
    - trigger next tournament tick when all matches finish
    """
    logger.info(
        "Handling MATCH_FINISHED command with payload: %s",
        payload,
    )

    match_id = payload.get("match_id")
    tournament_id = payload.get("tournament_id")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    if not match_id:
        raise ValueError("MATCH_FINISHED missing match_id")

    if not tournament_id:
        raise ValueError("MATCH_FINISHED missing tournament_id")

    # ------------------------------------------------------------------
    # Tournament round barrier tracking
    # ------------------------------------------------------------------

    redis_client = get_redis_client()

    active_matches_key = tournament_active_matches(tournament_id)

    removed = await redis_client.srem(
        active_matches_key,
        match_id,
    )

    if not removed:
        logger.warning(
            "Match %s was not present in active set for tournament %s",
            match_id,
            tournament_id,
        )

    remaining_matches = await redis_client.scard(
        active_matches_key,
    )

    logger.info(
        "Tournament %s has %s remaining active matches.",
        tournament_id,
        remaining_matches,
    )

    # ------------------------------------------------------------------
    # Round completion barrier reached
    # ------------------------------------------------------------------

    if remaining_matches == 0:
        logger.info(
            "All matches finished for tournament %s. Triggering next tournament tick.",
            tournament_id,
        )

        celery_app.send_task(
            "run_games",
            args=[tournament_id],
        )


async def handle_tournament_finished(
    app: FastAPI,
    payload: dict,
) -> None:
    """
    Handle TOURNAMENT_FINISHED events emitted by the tournament engine.

    Responsibilities:
    - start next tournament
    """

    logger.info(
        "Tournament %s finished. Starting next tournament.",
        payload.get("tournament_id"),
    )

    start_tennis_tournament.apply_async(countdown=30)
