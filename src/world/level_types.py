"""Value types for the building layout: floor kinds, cell kinds and per-level counts.

No pygame dependency.
"""

from dataclasses import dataclass
from enum import IntEnum


class FloorType(IntEnum):
    """Floor kinds as numbered in the exe's floor-type sequence."""
    GROUND = 0
    SECOND = 1
    BRICK_SHORT = 2
    BRICK_TALL = 3
    ROOF = 4


class CellKind(IntEnum):
    """Kinds of cell that can occupy a window slot; the values are the exe's cell types."""
    PLAIN = 0  # stone-floor window
    DOOR = 1
    ARCHED = 2
    PEDIMENT_A = 3  # brick-floor side window
    PEDIMENT_B = 4  # brick-floor center window


@dataclass(frozen=True)
class LevelConfig:
    """Per-level counts that scale with difficulty; hazard counts are per section."""
    floor_count: int
    section_count: int
    bird_pairs: int
    sill_obstacles: int
    drop_hazards: int
