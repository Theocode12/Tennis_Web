import asyncio
from abc import ABC, abstractmethod
from asyncio import Event, Task, create_task, sleep, CancelledError
from typing import Any, Dict, Optional, Callable, Awaitable, AsyncIterator

from backend.app.broker.message_broker import MessageBroker
from backend.app.shared.enums.broker_channels import BrokerChannels
from .game_feeder import BaseGameFeeder
from enum import StrEnum, auto

class SchedulerState(StrEnum):
    NOT_STARTED = auto()
    PAUSED = auto()
    ONGOING = auto()


class BaseScheduler(ABC):
    """Abstract base class for schedulers."""
    game_id: str
    broker: MessageBroker

    def __init__(self, game_id: str, broker: MessageBroker) -> None:
        self.game_id = game_id
        self.broker = broker

    @abstractmethod
    async def get_metadata(self)-> dict:
        raise NotImplementedError

    async def publish(self, channel: str, message: Any) -> None:
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
    """Schedules game score updates based on a feeder."""
    feeder: BaseGameFeeder
    pause_event: Event
    speed: float
    _current_sleep: Optional[Task[None]]
    controls: Dict[str, Callable[..., Awaitable[None]]] # Maps control names to async methods
    state: SchedulerState

    def __init__(self, game_id: str, broker: MessageBroker, feeder: BaseGameFeeder, game_speed: float = 1.0) -> None:
        super().__init__(game_id, broker)
        self.feeder = feeder
        self.pause_event = Event()
        self.speed = game_speed
        self._current_sleep = None
        self.controls = {
            'start': self.start,
            'pause': self.pause,
            'resume': self.resume,
            'adjust_speed': self.adjust_speed
        }
        self.state = SchedulerState.NOT_STARTED

    async def get_metadata(self)-> dict:
        game_metadata = await self.feeder.get_metadata()
        return {
            'game_state': self.state,
            **game_metadata
        }

    def _score_wrapper(self, score: dict):
        return {
                'data': score,
                'type': 'score_update'
            }

    async def run(self) -> None:
        """Optimized game loop with batched feeding and control handling."""
        
        # Start listening for control messages in the background
        control_task = create_task(self.subscribe_to_controls())

        try:
            score_iterator: AsyncIterator[Any] = self.feeder.get_next_score()
            async for score in score_iterator:
                # Wait if paused. The event is set by resume() or start()
                await self.pause_event.wait()

                await self.publish(BrokerChannels.SCORES_UPDATE, self._score_wrapper(score))

                # Adjustable sleep with immediate cancellation possibility
                try:
                    self._current_sleep = create_task(sleep(self.speed))
                    await self._current_sleep
                except CancelledError:
                    pass
                finally:
                    self._current_sleep = None

        except Exception as e:
            print(f"Error in GameScheduler run loop for {self.game_id}: {e}")
        finally:
            control_task.cancel() # Stop listening for controls
            try:
                await control_task
            except CancelledError:
                pass
            await self.feeder.cleanup() # type: ignore
            print(f"GameScheduler for {self.game_id} finished.")


    async def start(self) -> None:
        """Start or resume game updates by setting the event."""
        print(f"Starting scheduler for {self.game_id}")
        self.pause_event.set()
        self.state = SchedulerState.ONGOING

    async def pause(self) -> None:
        """Pause game updates efficiently by clearing the event and cancelling sleep."""
        print(f"Pausing scheduler for {self.game_id}")
        self.pause_event.clear()
        self.state = SchedulerState.PAUSED
        if self._current_sleep and not self._current_sleep.done():
            self._current_sleep.cancel()

    async def resume(self) -> None:
        """Resume game updates by setting the event."""
        print(f"Resuming scheduler for {self.game_id}")
        self.pause_event.set()
        self.state = SchedulerState.ONGOING

    async def adjust_speed(self, new_speed: float) -> None:
        """Change game speed with immediate effect."""
        print(f"Adjusting speed for {self.game_id} to {new_speed}")
        if new_speed <= 0:
            print(f"Warning: Invalid speed {new_speed} requested. Speed must be positive.")
            return # Or raise an error

        self.speed = new_speed
        # If currently sleeping, cancel the existing sleep task
        if self._current_sleep and not self._current_sleep.done():
            self._current_sleep.cancel()

    async def subscribe_to_controls(self) -> None:
        """Handle control messages efficiently."""
        print(f"Scheduler {self.game_id} subscribing to control messages.")
        try:
            # Assuming broker.subscribe yields messages for the specific game_id and "controls" channel
            control_iterator: AsyncIterator[Dict[str, Any]] = self.broker.subscribe(self.game_id, BrokerChannels.CONTROLS) # Specify channel
            async for message in control_iterator:
                command_type = message.get('type')
                handler = self.controls.get(command_type)

                if handler:
                    print(f"Scheduler {self.game_id} received control: {message}")
                    if command_type == 'adjust_speed':
                        speed_value = message.get('speed')
                        if isinstance(speed_value, (int, float)):
                            await handler(float(speed_value))
                        else:
                            print(f"Invalid speed value received: {speed_value}")
                    else:
                        # For start, pause, resume which don't need extra args
                        await handler()
                else:
                    print(f"Scheduler {self.game_id} received unknown control type: {command_type}")
        except asyncio.CancelledError:
            print(f"Control subscription for {self.game_id} cancelled.")
            raise
        except Exception as e:
            print(f"Error in control subscription for {self.game_id}: {e}")
        finally:
            print(f"Scheduler {self.game_id} unsubscribed from controls.")