from typing import Any, Protocol


class SchedulerStatePublisher(Protocol):
    async def publish_state(
        self,
        *,
        game_id: str,
        state: dict[str, Any],
    ) -> None:
        ...

    async def cleanup(self, *, game_id: str) -> None:
        ...
