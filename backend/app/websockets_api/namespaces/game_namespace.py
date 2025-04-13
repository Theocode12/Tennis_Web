import logging
from typing import  Optional, Any
from socketio import AsyncNamespace
from pydantic import ValidationError
from backend.app.core.context import AppContext
from backend.app.shared.enums.client_events import ClientEvent
from app.websockets_api.routes.registry import ROUTES, RouteDefinition

logger = logging.getLogger(__name__)

class GameNamespace(AsyncNamespace):
    """
    Handles all client interactions within the '/game' namespace.

    Manages connections, disconnections, message routing, validation,
    and cleanup related to game interactions.
    """
    context: AppContext

    def __init__(self, namespace: str, context: AppContext):
        """
        Initializes the GameNamespace.

        Args:
            namespace: The namespace identifier (e.g., '/game').
            context: The application context containing shared resources.
        """
        super().__init__(namespace)
        self.context = context
        logger.info(f"GameNamespace initialized for namespace '{namespace}'")

    async def on_connect(self, sid: str, environ: dict):
        """Handles a new client connection to the /game namespace."""
        logger.info(f'Client connected to namespace {self.namespace}: SID={sid}')
        # TODO: Add initial authentication/validation if needed using environ or an initial auth message

    async def on_disconnect(self, sid: str):
        """Handles a client disconnection from the /game namespace."""
        try:
            # Note: sio.rooms(sid) includes the client's own SID room
            client_rooms = self.context.sio.rooms(sid, namespace=self.namespace)
            logger.debug(f"Client {sid} was in rooms within {self.namespace}: {client_rooms}")

            for room in client_rooms:
                # Skip the client's own default room (named after their SID)
                if room == sid:
                    continue

                logger.info(f"Removing client {sid} from room {room} in namespace {self.namespace}")
                await self.leave_room(sid, room)

        except Exception as e:
            logger.error(f"Error during disconnect cleanup for SID {sid} in namespace {self.namespace}: {e}", exc_info=True)

    async def on_message(self, sid: str, data: Any):
        """Handles generic 'message' events sent by the client."""
        logger.debug(f"Received 'message' event from {sid} in {self.namespace}: {data}")
        if not isinstance(data, dict):
             await self.emit(ClientEvent.ERROR.value, {"error": "Invalid message format, expected object"}, to=sid)
             return
        await self._handle_incoming_message(sid, data)


    async def _handle_incoming_message(self, sid: str, data: dict):
        action = data.get("type")
        if not action:
            await self.emit("error", {"error": "Message type missing"}, to=sid)
            return
        
        route_definition: Optional[RouteDefinition] = ROUTES.get(action)

        if not route_definition:
            await self.emit(ClientEvent.ERROR, {"error": "Unknown message type"}, to=sid)
            return

        try:
            validated_data = route_definition["schema"](**data).model_dump()
        except ValidationError as e:
            await self.emit(ClientEvent.ERROR, {"error": "data schema is invalid"}, to=sid)
            return
        try:
            handler = route_definition['handler'](self)
            await handler.handle(sid, validated_data)
        except Exception as e:
            await self.emit(
                ClientEvent.ERROR.value,
                {"error": f"An internal error occurred while processing '{action}'."},
                to=sid,
            )