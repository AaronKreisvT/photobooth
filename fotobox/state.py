from enum import Enum, auto

class AppState(Enum):
    MAIN = auto()
    PREVIEW = auto()
    PROCESSING = auto()
    FINAL = auto()
    END = auto()
    SCREENSAVER = auto()
