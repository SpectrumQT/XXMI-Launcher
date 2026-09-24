from enum import Enum, auto


class Stage(Enum):
    Ready = auto()
    Busy = auto()
    Download = auto()
