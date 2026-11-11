"""Exe animation records, as the animation table at 0x419800 stores them.

No pygame dependency.
"""

from dataclasses import dataclass
from enum import IntEnum


class AnimationMode(IntEnum):
    """Animation table field +4, as FUN_0040ed40 reads it."""
    STATIC = 0  # never advances
    LOOP = 1  # wraps to frame 0
    ONCE = 2  # clamps on the last frame and sets the node's "finished" flag


@dataclass(frozen=True)
class AnimationFrame:
    """One 10-byte frame record: right-facing frame id, hold, origin.

    The left-facing id is omitted: no node built from these records faces left.
    FUN_0040ee00 draws the frame's top-left at (x - origin_x, y - origin_y).
    """
    frame_id: int
    hold: int
    origin_x: int
    origin_y: int


@dataclass(frozen=True)
class Animation:
    """One entry of the exe animation table at 0x419800 (12 bytes each)."""
    mode: AnimationMode
    frames: tuple[AnimationFrame, ...]


def frame_display_ticks(hold_ticks: int) -> int:
    """Ticks a frame stays up: FUN_0040ed40 counts the hold down to zero before advancing."""
    return hold_ticks + 1
