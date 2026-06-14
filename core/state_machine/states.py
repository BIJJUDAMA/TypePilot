from enum import Enum, auto

class AppState(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    INJECTING = auto()
    ERROR = auto()
