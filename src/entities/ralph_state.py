"""Ralph's state machine states (the exe's +0x734)."""

from enum import Enum, auto


class RalphState(Enum):
    WALK = auto()
    POUND = auto()
    SECTION_POSE = auto()
    CLIMB = auto()
    RAGE = auto()
    IDLE = auto()
