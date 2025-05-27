from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError
from socketio import AsyncNamespace

from app.shared.enums.client_events import ClientEvent

if TYPE_CHECKING:
    from app.core.context import AppContext


class GameNamespace(AsyncNamespace):  # type: ignore[misc]
    """
    Handles all client interactions within the '/game' namespace.

    Manages connections, disconnections, message routing, validation,
    and cleanup for game-related interactions.
    """

    context: AppContext

    def __init__(self, namespace: str, context: AppContext) -> None:
        """
        Initializes the GameNamespace.

        Args:
            namespace: The namespace identifier (e.g., '/game').
            context: The application context containing shared resources.
        """
        super().__init__(namespace)
        self.context = context
        self.logger = context.logger
        self.logger.info(f"GameNamespace initialized for '{namespace}' namespace.")

    async def on_connect(self, sid: str, environ: dict[str, Any]) -> None:
        """
        Handles a new client connection to the '/game' namespace.

        Args:
            sid: The session ID of the client.
            environ: The environment dictionary provided by the connection.
        """
        # self.logger.info(
        #     f"Client connected to namespace {self.namespace}: SID={sid}"
        #     f" with environ={environ}"
        # )
        # TODO: Implement authentication/validation logic using environ or an
        #        initial auth message if needed

    async def on_disconnect(self, sid: str) -> None:
        """
        Handles a client disconnection from the '/game' namespace.

        Args:
            sid: The session ID of the disconnected client.
        """
        try:
            # Retrieve the rooms the client is part of
            client_rooms = self.context.sio.rooms(sid, namespace=self.namespace)
            self.logger.debug(f"Client {sid} was in rooms: {client_rooms}")

            for room in client_rooms:
                if room == sid:
                    continue  # Skip the client's default room

                self.logger.info(
                    f"Removing client {sid} from room {room} in "
                    f"namespace {self.namespace}"
                )
                await self.leave_room(sid, room)

                # Get the list of participants and check if the room is now empty
                participants = list(
                    self.context.client_manager.get_participants(
                        self.namespace, room
                    )
                )

                if not participants:
                    self.logger.info(
                        f"Room {room} in namespace {self.namespace} is empty, "
                        "performing cleanup."
                    )

                    await self.close_room(room)

        except Exception as e:
            self.logger.error(
                f"Error during disconnect cleanup for SID {sid}: {e}", exc_info=True
            )

    async def on_message(
        self, sid: str, data: Any
    ) -> None:  # should take in a variadic
        """
        Handles incoming 'message' events sent by the client.

        Args:
            sid: The session ID of the client sending the message.
            data: The data sent by the client.
        """
        self.logger.debug(f"Received 'message' event from SID {sid}: {data}")

        if not isinstance(data, dict):
            error_msg = {"error": "Invalid message format, expected an object"}
            await self.emit(ClientEvent.ERROR, error_msg, to=sid)
            return

        data["namespace"] = self.namespace
        await self._handle_incoming_message(sid, data)

    async def _handle_incoming_message(self, sid: str, data: dict[str, Any]) -> None:
        """
        Processes the incoming message and routes it to the appropriate handler.

        Args:
            sid: The session ID of the client sending the message.
            data: The validated message data.
        """
        message_type = data.get("type")

        if not message_type:
            error_msg = {"error": "Message type missing"}
            await self.emit(ClientEvent.ERROR, error_msg, to=sid)
            return

        router = self.context.router
        route_definition = router.get_definition(message_type)

        if route_definition is None:
            error_msg = {"error": "Unknown message type"}
            await self.emit(ClientEvent.ERROR, error_msg, to=sid)
            return

        try:
            schema_cls = route_definition.get("schema")
            print(data)
            validated_data = (
                data if schema_cls is None else schema_cls(**data).model_dump()
            )
            print(validated_data)
        except ValidationError:
            error_msg = {"error": "Invalid data schema"}
            await self.emit(ClientEvent.ERROR.value, error_msg, to=sid)
            return

        try:
            handler = route_definition["handler"](self.context)
            await handler.handle(sid, validated_data)
        except Exception as e:
            self.logger.error(
                f"Error processing '{message_type}' for SID {sid}: {e}",
                exc_info=True,
            )
            error_msg = {
                "error": "An internal error occurred while processing the message"
            }
            await self.emit(ClientEvent.ERROR, error_msg, to=sid)
