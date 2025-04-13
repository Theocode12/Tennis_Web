from enum import StrEnum
from enum import auto


class BrokerChannels(StrEnum):
    CONTROLS = auto()
    SCORES_UPDATE = auto()