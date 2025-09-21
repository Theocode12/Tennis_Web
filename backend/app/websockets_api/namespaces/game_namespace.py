from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base_namespace import BaseNamespace

if TYPE_CHECKING:
    from app.core.context import AppContext


class GameNamespace(BaseNamespace):
    """
    Handles all client interactions within the '/game' namespace.

    Manages connections, disconnections, message routing, validation,
    and cleanup for game-related interactions.
    """

    context: AppContext

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
