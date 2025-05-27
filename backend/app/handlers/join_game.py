from __future__ import annotations

import asyncio
from typing import Any, Literal

from pydantic import BaseModel

from app.core.context import AppContext
from app.handlers.base import BaseHandler
from app.shared.enums.broker_channels import BrokerChannels
from app.shared.enums.client_events import ClientEvent
from app.shared.enums.message_types import MessageType


def create_subscription_key(game_id: str, channels: list[BrokerChannels]) -> str:
    """
    Creates a unique subscription key based on the game ID and channels.
    This key is used to manage broker listener tasks.

    Args:
        game_id (str): Unique identifier for the game session.
        channels (list[BrokerChannels]): List of channels to subscribe to.

    Returns:
        str: A unique subscription key in the format
                "game_id:channel1:channel2:...".
    """
    return f"{game_id}:{':'.join(sorted([ch.value for ch in channels]))}"


def get_game_id_from_subscription_key(subscription_key: str) -> str:
    """
    Extracts the game ID from a subscription key.

    Args:
        subscription_key (str): The subscription key in the format
                                "game_id:channel1:channel2:...".

    Returns:
        str: The game ID extracted from the subscription key.
    """
    return subscription_key.split(":")[0]


async def listen_to_broker_channels(
    context: AppContext, game_id: str, channels: list[BrokerChannels], namespace: str
) -> None:
    """
    Subscribes to broker channels for a given game ID, listens for
    incoming messages, and emits structured events to the associated Socket.IO room.

    Message types are used to determine which client event should be triggered.

    Args:
        context (AppContext): Application context with broker, logger,
                                and socket server.
        game_id (str): Identifier for the game session (also used as room name).
        channels (list[BrokerChannels]): Channels to subscribe to for
                                         broker messages.

    Behavior:
        - Emits `ClientEvent.GAME_SCORE_UPDATE` on "score_update" messages.
        - Emits corresponding `ClientEvent` for known "game.control.*" messages.
        - Ignores unknown or malformed messages.
    """
    logger = context.logger

    try:
        message_iterator = await context.broker.subscribe(game_id, channels)

        async for message_data in message_iterator:
            logger.debug(
                f"Received message for game_id={game_id}, "
                f"channels={channels}: {message_data}"
            )

            if not isinstance(message_data, dict):
                logger.debug("Skipped non-dict broker message.")
                continue

            msg_type_str = message_data.get("type")
            if not msg_type_str:
                logger.debug("Skipped broker message without 'type' field.")
                continue

            client_event = None
            client_payload_data = {}

            if msg_type_str == "score_update":
                client_event = ClientEvent.GAME_SCORE_UPDATE
                score_payload = message_data.get("data")
                if isinstance(score_payload, dict):
                    client_payload_data = score_payload
                else:
                    logger.warning(
                        "Skipped invalid 'score_update' message for "
                        f"game_id={game_id}: missing or malformed 'data' field."
                    )
                    continue

            elif msg_type_str.startswith("game.control."):
                try:
                    client_event = ClientEvent(msg_type_str)
                    client_payload_data = message_data.copy()
                    client_payload_data.pop("token", None)
                    client_payload_data.pop("type", None)
                except ValueError:
                    logger.warning(
                        "Unknown control type received in broker for "
                        f"game_id={game_id}: {msg_type_str}"
                    )
                    continue
            else:
                logger.debug(
                    f"Skipped unknown broker message type for game_id={game_id}: "
                    f"{msg_type_str}"
                )
                continue

            if client_event:
                final_client_payload = {
                    "type": client_event,
                    "game_id": game_id,
                    **client_payload_data,
                }

                await context.sio.emit(
                    client_event.value,
                    final_client_payload,
                    room=game_id,
                    namespace=namespace,
                )
                logger.debug(
                    f"Emitted event '{client_event.value}' to room "
                    f"'{game_id}' with payload: {final_client_payload}"
                )

    except asyncio.CancelledError:
        raise  # Allow graceful cancellation
    except Exception as e:
        logger.error(
            f"Exception in broker listener for game_id={game_id}, "
            f"channels={channels}: {e}",
            exc_info=True,
        )
    finally:
        logger.info(
            f"Listener task finished for game_id={game_id}, channels={channels}."
        )


def _cleanup_listener_task(
    task: asyncio.Task[Any],
    context: AppContext,
    subscription_key: str,
    namespace: str,
) -> None:
    """
    Cleans up a finished broker listener task.

    Args:
        task: The asyncio task that has completed.
        context: The application context holding task state and logger.
        subscription_key: Unique key identifying the listener task to be removed.

    Removes the task from the context registry and logs any unhandled exceptions
    (excluding cancellations).
    """
    logger = context.logger
    logger.info(
        f"JoinGameHandler: Running cleanup for listener task '{task.get_name()}' "
        f"({subscription_key=})"
    )

    # Safely remove the finished task from the active registry
    context.broker_listener_tasks.pop(subscription_key, None)

    game_id = get_game_id_from_subscription_key(subscription_key)
    context.client_manager.close_room(game_id, namespace)

    # Log exception if it's not a clean cancellation
    exception = task.exception()
    if exception and not isinstance(exception, asyncio.CancelledError):
        logger.error(
            f"JoinGameHandler: Listener task for {subscription_key=} ended "
            f"with an error: {exception}",
            exc_info=exception,
        )


class JoinGameHandler(BaseHandler):
    """
    Handles a client's request to join a game.

    Verifies the game is active, starts a broker listener if needed,
    adds the client to the appropriate Socket.IO room, and sends back game metadata.
    """

    context: AppContext

    async def handle(self, sid: str, data: dict[str, Any]) -> None:
        """
        Process a 'join game' request from a client and respond with game metadata.

        Args:
            sid (str): Socket.IO session ID of the client.
            data (dict): Incoming request payload containing at least 'game_id'.
        """
        context = self.context
        logger = context.logger
        namespace = data.get("namespace", "/game")
        game_id = data.get("game_id")

        if not game_id:
            logger.warning(
                f"JoinGameHandler: Missing game_id in client data from {sid}"
            )
            await context.sio.emit(
                ClientEvent.ERROR,
                {"error": "Missing required 'game_id' field."},
                to=sid,
                namespace=namespace,
            )
            return

        scheduler = context.scheduler_manager.get_scheduler(game_id)
        if not scheduler:
            logger.warning(
                f"JoinGameHandler: Game '{game_id}' not found or inactive."
            )
            await context.sio.emit(
                ClientEvent.ERROR.value,
                {
                    "error": f"Game '{game_id}' is not currently active or "
                    "does not exist."
                },
                to=sid,
                namespace=namespace,
            )
            return

        channels_to_listen = [BrokerChannels.SCORES_UPDATE, BrokerChannels.CONTROLS]
        subscription_key = create_subscription_key(game_id, channels_to_listen)
        if subscription_key not in context.broker_listener_tasks:
            logger.info(
                f"JoinGameHandler: No broker listener for game_id={game_id}"
                f"and channels={channels_to_listen}. Creating listener task."
            )
            listener_task = asyncio.create_task(
                listen_to_broker_channels(
                    context, game_id, channels_to_listen, namespace
                ),
                name=f"broker_listener_{subscription_key}",
            )
            context.broker_listener_tasks[subscription_key] = listener_task
            namespace = data.get("namespace", "/game")
            listener_task.add_done_callback(
                lambda t: _cleanup_listener_task(
                    t, context, subscription_key, namespace
                )
            )
            logger.info(
                f"JoinGameHandler: Broker listener task for {subscription_key}"
                " created and registered."
            )
        else:
            logger.info(
                "JoinGameHandler: Reusing existing broker listener "
                f"for {subscription_key}."
            )

        try:
            await context.sio.enter_room(sid, game_id, namespace=namespace)
            logger.info(
                f"JoinGameHandler: Client {sid} entered Socket.IO room {game_id}"
            )

            response_data = await scheduler.get_metadata()
            await context.sio.emit(
                ClientEvent.GAME_JOIN,
                {**response_data, "message": f"Successfully joined game {game_id}"},
                to=sid,
                namespace=namespace,
            )
        except Exception as e:
            logger.error(
                f"JoinGameHandler: Failed to add client {sid} to "
                f"room {game_id}: {e}",
                exc_info=True,
            )
            await context.sio.emit(
                ClientEvent.ERROR,
                {"error": f"Failed to enter game room '{game_id}'."},
                to=sid,
                namespace=namespace,
            )


class JoinGameSchema(BaseModel):
    game_id: str
    type: Literal[MessageType.GAME_JOIN]
