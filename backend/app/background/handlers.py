from fastapi import FastAPI

from utils.logger import get_logger

logger = get_logger()


async def handle_command(
    app: FastAPI,
    message_id: str,
    payload: dict,
) -> None:
    command_type = payload.get("type")

    if command_type == "START_MATCH":
        await handle_start_match(app, payload)
    else:
        logger.warning(f"Unknown command type: {payload}")


async def handle_start_match(app: FastAPI, payload: dict) -> None:
    match_id = payload.get("match_id")
    if not match_id:
        raise ValueError("Missing match_id")

    logger.info(f"START_MATCH received: {match_id}")

    sio_context = app.state.sio_context
    scheduler_manager = sio_context.get_scheduler_manager()

    scheduler, _ = await scheduler_manager.create_or_get_scheduler(
        game_id=str(match_id)
    )
    await scheduler.start()
