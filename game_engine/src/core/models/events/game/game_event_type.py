from ..event_type import EventType


class GameEventType(EventType):
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    FINISH = "finish"
    ERROR = "error"
    SCORES = "scores"
    GAME_OVER = "game_over"
