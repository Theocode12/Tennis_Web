from __future__ import annotations

import configparser
import logging
from abc import ABC, abstractmethod
from asyncio import CancelledError, Event, Task, create_task, sleep
from collections.abc import AsyncGenerator, Awaitable, Callable
from enum import StrEnum, auto
from typing import Any

from app.broker.message_broker import MessageBroker
from app.shared.enums.broker_channels import BrokerChannels
from app.shared.enums.client_events import ClientEvent
from app.shared.enums.control_types import Controls
from utils.load_config import load_config
from utils.logger import get_logger

from .game_feeder import BaseGameFeeder


class SchedulerState(StrEnum):
    NOT_STARTED = auto()
    PAUSED = auto()
    ONGOING = auto()
    AUTOPLAY = auto()


class SchedulerCommands(StrEnum):
    """Enum representing valid scheduler control commands."""

    START = Controls.GAME_CONTROL_START
    PAUSE = Controls.GAME_CONTROL_PAUSE
    RESUME = Controls.GAME_CONTROL_RESUME
    ADJUST_SPEED = Controls.GAME_CONTROL_SPEED


class BaseScheduler(ABC):
    """Abstract base class for schedulers."""

    game_id: str
    broker: MessageBroker

    def __init__(self, game_id: str, broker: MessageBroker) -> None:
        self.game_id = game_id
        self.broker = broker

    @abstractmethod
    async def get_metadata(self) -> dict[str, Any]:
        raise NotImplementedError

    async def publish(self, channel: BrokerChannels, message: Any) -> None:
        """Publish data to the game channel."""
        await self.broker.publish(self.game_id, channel, message)

    @abstractmethod
    async def run(self) -> None:
        """Run the scheduler's main loop."""
        raise NotImplementedError

    @abstractmethod
    async def start(self) -> None:
        """Start the scheduler's operation."""
        raise NotImplementedError

    @abstractmethod
    async def pause(self) -> None:
        """Pause the scheduler's operation."""
        raise NotImplementedError

    @abstractmethod
    async def resume(self) -> None:
        """Resume the scheduler's operation."""
        raise NotImplementedError

    @abstractmethod
    async def adjust_speed(self, new_speed: float) -> None:
        """Adjust the operational speed of the scheduler."""
        raise NotImplementedError

    @abstractmethod
    async def subscribe_to_controls(self) -> None:
        """Subscribe to and handle control messages."""
        raise NotImplementedError


class GameScheduler(BaseScheduler):
    """
    Schedules game score updates by consuming scores from a
    feeder and publishing them.
    """

    score_update_sleep_task: Task[None] | None
    feeder: BaseGameFeeder
    pause_event: Event
    speed: float
    controls: dict[str, Callable[..., Awaitable[None]]]
    state: SchedulerState

    def __init__(
        self,
        game_id: str,
        broker: MessageBroker,
        feeder: BaseGameFeeder,
        config: configparser.ConfigParser | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Initialize the GameScheduler.

        Args:
            game_id (str): Identifier for the game being scheduled.
            broker (MessageBroker): Message broker instance to publish
                                    and subscribe messages.
            feeder (BaseGameFeeder): Feeder instance to get game score updates.
            game_speed (float): Delay (in seconds) between score updates.
            config (Optional[ConfigParser]): Configuration object for scheduler.
            logger (Optional[Logger]): Logger for debugging and error reporting.
        """
        super().__init__(game_id, broker)
        self.config = config or load_config()
        self.logger = logger or get_logger(self.__class__.__name__)
        self.feeder = feeder
        self.pause_event = Event()
        self.speed = self.config.getfloat("app", "defaultGameSpeed", fallback=1.0)
        self.score_update_sleep_task: Task[None] | None = None
        self.state = SchedulerState.NOT_STARTED
        self.pause_timeout_secs = self.config.getfloat(
            "app", "pauseTimeoutSecs", fallback=60.0
        )
        self._pause_timer: Task[None] | None = None

        self.controls = {
            SchedulerCommands.START: self.start,
            SchedulerCommands.PAUSE: self.pause,
            SchedulerCommands.RESUME: self.resume,
            SchedulerCommands.ADJUST_SPEED: self.adjust_speed,
        }

    async def get_metadata(self) -> dict[str, Any]:
        """
        Get current scheduler metadata, including game state and game details.

        Returns:
            dict[str, Any]: Combined metadata payload.
        """
        game_details = await self.feeder.get_game_details()
        return {"game_state": self.state, **game_details}

    def _format_score_update_payload(self, score: dict[str, Any]) -> dict[str, Any]:
        """
        Format a score dictionary into the standard broker payload format.

        Args:
            score (dict): Score data.

        Returns:
            dict[str, Any]: Payload formatted for broker publishing.
        """
        return {
            "data": score,
            "type": ClientEvent.GAME_SCORE_UPDATE,
        }

    def _start_pause_timer(self) -> None:
        """Starts a TTL countdown for paused state, if configured."""
        if not self.pause_timeout_secs:
            return

        async def _timer() -> None:
            await sleep(self.pause_timeout_secs)
            if not self.pause_event.is_set():
                self.logger.warning(
                    f"Game {self.game_id} paused "
                    f"too long (>{self.pause_timeout_secs}s);"
                    "SHUTTING DOWN SCHEDULER ..."
                )
                await self.resume_due_to_timeout()

        self._pause_timer = create_task(_timer())

    def _cancel_pause_timer(self) -> None:
        """Cancels the pause TTL countdown, if running."""
        if self._pause_timer and not self._pause_timer.done():
            self.logger.debug("Canceling Pause Timer")
            self._pause_timer.cancel()
            self._pause_timer = None

    async def resume_due_to_timeout(self) -> None:
        """
        Handles AutoPlay when the scheduler is paused for too long.

        Side Effects:
            - Cancels the game loop.
            - Sets internal state to AUTOPLAY.
        """
        self.logger.info(
            f"Resuming scheduler for {self.game_id} due to pause timeout."
        )
        self.state = SchedulerState.AUTOPLAY
        self.pause_event.set()  # Unblock the pause wait
        if self.score_update_sleep_task and not self.score_update_sleep_task.done():
            self.score_update_sleep_task.cancel()
        self._cancel_pause_timer()

    async def run(self) -> None:
        """
        Main game loop that fetches scores from the feeder and publishes them.

        Handles control messages asynchronously and respects pause/resume/speed
         state.
        """
        control_task = create_task(self.subscribe_to_controls())

        try:
            score_iterator: AsyncGenerator[Any, None] = self.feeder.get_next_score()

            async for score in score_iterator:
                await self.pause_event.wait()

                await self.publish(
                    BrokerChannels.SCORES_UPDATE,
                    self._format_score_update_payload(score),
                )

                try:
                    self.score_update_sleep_task = create_task(sleep(self.speed))
                    await self.score_update_sleep_task
                except CancelledError:
                    self.logger.debug(
                        "Sleep interrupted during pause or speed change."
                    )
                finally:
                    self.score_update_sleep_task = None

        except Exception:
            self.logger.exception(f"Run loop error for game_id={self.game_id}")
            raise
        finally:
            control_task.cancel()
            try:
                await control_task
            except CancelledError:
                self.logger.debug("Control task cancelled cleanly.")

            await self.feeder.cleanup()
            self.logger.info(f"Scheduler finished for game_id={self.game_id}.")

    async def start(self) -> None:
        """
        Start or resume the game scheduler.

        Side Effects:
            - Sets the pause event.
            - Updates internal scheduler state.
        """
        self.logger.info(f"Starting scheduler for game_id={self.game_id}")
        self.pause_event.set()
        self.state = SchedulerState.ONGOING

    async def pause(self) -> None:
        """
        Pause the game scheduler.

        Side Effects:
            - Clears the pause event.
            - Cancels current sleep task.
            - Updates internal scheduler state.
        """
        self.logger.info(f"Pausing scheduler for game_id={self.game_id}")
        self.pause_event.clear()
        self.state = SchedulerState.PAUSED
        self._start_pause_timer()

        if self.score_update_sleep_task and not self.score_update_sleep_task.done():
            self.score_update_sleep_task.cancel()

    async def resume(self) -> None:
        """
        Resume game updates after a pause.

        Side Effects:
            - Sets the pause event.
            - Updates internal scheduler state.
        """
        self.logger.info(f"Resuming scheduler for game_id={self.game_id}")
        self.pause_event.set()
        self._cancel_pause_timer()
        self.state = SchedulerState.ONGOING

    async def adjust_speed(self, new_speed: float) -> None:
        """
        Dynamically adjust the update speed of the game scheduler.

        Args:
            new_speed (float): New delay in seconds between score updates.

        Side Effects:
            - Updates internal sleep duration.
            - Cancels current sleep task if one is running.
        """
        if new_speed <= 0:
            self.logger.warning(
                f"Ignored invalid speed={new_speed} for game_id={self.game_id}"
            )
            return

        self.logger.info(
            f"Adjusting speed for game_id={self.game_id} to speed={new_speed}"
        )
        self.speed = new_speed

        if self.score_update_sleep_task and not self.score_update_sleep_task.done():
            self.logger.debug("Cancelling score update sleep task if available")
            self.score_update_sleep_task.cancel()

    async def subscribe_to_controls(self) -> None:
        """
        Subscribe to control commands for this game and route them to their handlers.

        Listens asynchronously for messages on the controls channel.
        """
        self.logger.debug(
            f"Scheduler for game_id={self.game_id} subscribing to controls."
        )

        try:
            control_iterator: AsyncGenerator[
                dict[str, Any], None
            ] = await self.broker.subscribe(self.game_id, BrokerChannels.CONTROLS)

            async for message in control_iterator:
                self.logger.debug(f"Received control message: {message}")
                command_type = message.get("type", "")
                handler = self.controls.get(command_type)

                if handler:
                    self.logger.info(
                        f"Received control={command_type} for game_id={self.game_id}"
                    )
                    if command_type == SchedulerCommands.ADJUST_SPEED:
                        speed_value = message.get("speed")
                        if isinstance(speed_value, (int | float)):
                            await handler(float(speed_value))
                        else:
                            self.logger.warning(
                                f"Ignored invalid speed value: {speed_value}"
                            )
                    else:
                        await handler()
                else:
                    self.logger.warning(
                        f"Unknown control type={command_type} "
                        f"for game_id={self.game_id}"
                    )

        except CancelledError:
            self.logger.debug(
                f"Control subscription cancelled for game_id={self.game_id}"
            )
            raise
        except Exception:
            self.logger.exception(
                f"Control subscription error for game_id={self.game_id}"
            )
        finally:
            self.logger.info(
                f"Scheduler unsubscribed from controls for game_id={self.game_id}."
            )
