import asyncio
import logging
from typing import Literal
from pydantic import BaseModel
from backend.app.handlers.base import BaseHandler
from app.websockets_api.routes.registry import register_route
from backend.app.shared.enums.message_types import MessageType
from backend.app.shared.enums.broker_channels import BrokerChannels
from backend.app.shared.enums.client_events import ClientEvent
from backend.app.core.context import AppContext

logger = logging.getLogger(__name__)

async def listen_to_broker_channels(context: AppContext, game_id: str, channels: list[str]):
    """
    Listens to multiple broker channels for a game_id and forwards messages
    to the corresponding Socket.IO room, mapping them to appropriate client events
    based on the 'type' field in the message data.
    """
    try:
        message_iterator = context.broker.subscribe(game_id, channels)

        async for message_data in message_iterator:
            if message_data is None: # Recieved sentinel value to terminate
                 break

            logger.debug(f"Broker message received for {game_id=} (channels={channels}): {message_data}")

            if not isinstance(message_data, dict):
                continue # Skip non-dict messages

            msg_type_str = message_data.get("type")
            if not msg_type_str:
                continue # Skip messages without a type

            client_event = None
            client_payload_data = {} # Data specific to the client event

            if msg_type_str == "score_update":
                client_event = ClientEvent.GAME_SCORE_UPDATE
                score_payload = message_data.get("data")
                if isinstance(score_payload, dict):
                     client_payload_data = score_payload
                else:
                     continue # Skip invalid score updates

            elif msg_type_str.startswith("game.control."):
                try:
                    client_event = ClientEvent(msg_type_str)
                    client_payload_data = message_data.copy() # Use copy to avoid modifying original
                    client_payload_data.pop("token", None)
                    client_payload_data.pop("type", None)
                except ValueError:
                    continue # Skip unknown control types
            else:
                continue # Skip other unknown types

            if client_event:
                final_client_payload = {
                    "type": client_event.value,
                    "game_id": game_id,
                    **client_payload_data # Spread the specific data (scores or controls)
                }
                await context.sio.emit(client_event.value, final_client_payload, room=game_id)

    except asyncio.CancelledError:
        raise # Important: Re-raise CancelledError
    except Exception as e:
        logger.error(f"Error in broker listener for {game_id=}, channels={channels}: {e}", exc_info=True)
    finally:
        logger.info(f"Broker listener task for {game_id=}, channels={channels} finished.")

def _cleanup_listener_task(task: asyncio.Task, context: AppContext, subscription_key: str):
    """Callback function to clean up resources when a listener task finishes."""
    logger.info(f"Running cleanup callback for listener task {task.get_name()} ({subscription_key=})")
    context.broker_listener_tasks.pop(subscription_key, None)

    exception = task.exception()
    if exception and not isinstance(exception, asyncio.CancelledError):
        logger.error(f"Listener task for {subscription_key=} finished with exception: {exception}", exc_info=exception)


class JoinGameHandler(BaseHandler):
    context: AppContext

    async def handle(self, sid: str, data: dict):
        game_id = data["game_id"]
        context = self.context

        scheduler = context.scheduler_manager.get_scheduler(game_id)
        if not scheduler:
            await context.sio.emit(ClientEvent.ERROR, {"error": f"Game '{game_id}' is not currently active or does not exist."}, to=sid)
            return

        channels_to_listen = [
            BrokerChannels.SCORES_UPDATE,
            BrokerChannels.CONTROLS
        ]

        # Generate a unique key for the subscription task based on game_id and sorted channels
        subscription_key = f"{game_id}:{':'.join(sorted([ch.value for ch in channels_to_listen]))}"


        # Check if a listener task for this *combination* of channels already exists
        if subscription_key not in context.broker_listener_tasks:
            logger.info(f"No active broker listener task for {game_id=} covering channels {channels_to_listen}. Setting up...")

            listener_task = asyncio.create_task(
                listen_to_broker_channels(context, game_id, channels_to_listen),
                name=f"broker_listener_{subscription_key}"
            )
            # Store the task using the unique key
            context.broker_listener_tasks[subscription_key] = listener_task

            # Add a callback to clean up using the subscription key
            listener_task.add_done_callback(
                lambda t: _cleanup_listener_task(t, context, subscription_key) # Pass key for cleanup
            )
            logger.info(f"Broker listener task for {subscription_key} created and stored.")
        else:
             logger.info(f"Broker listener task for {subscription_key} already exists.")


        try:
            await context.sio.enter_room(sid, game_id)
            logger.info(f"Client {sid} entered Socket.IO room {game_id}")
            response_data = scheduler.get_metadata()
            await context.sio.emit(ClientEvent.GAME_JOIN, {**response_data, "message": f"Successfully joined game {game_id}"}, to=sid)
        except Exception as e:
             logger.error(f"Failed to add client {sid} to room {game_id}: {e}", exc_info=True)
             await context.sio.emit(ClientEvent.ERROR, {"error": f"Failed to enter game room {game_id}"}, to=sid)


class JoinGameSchema(BaseModel):
    game_id: str
    type: Literal[MessageType.GAME_JOIN]


register_route(message_type=MessageType.GAME_JOIN, handler=JoinGameHandler, schema=JoinGameSchema)
