"""Per-level building layout: floor sequences, hazard counts and cell geometry.

Pure data plus two lookup functions; no pygame dependency.
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


FLOORS_PER_SECTION = 4  # [EXE] FUN_00409610
MAX_CONFIGURED_LEVEL = 10  # [EXE] config table 0x419d78 is capped at level 10
FACADE_X = 8  # [EXE] floor art is drawn at x = 8
FACADE_WIDTH = 224  # [EXE] centered on the 240-wide screen
STREET_Y = 320  # bottom of the logical screen; ground floor sits on it

# [EXE] layout heights; the roof's art is 160px tall but its layout row is 56.
FLOOR_HEIGHT: dict[FloorType, int] = {
    FloorType.GROUND: 56,
    FloorType.SECOND: 56,
    FloorType.BRICK_SHORT: 48,
    FloorType.BRICK_TALL: 56,
    FloorType.ROOF: 56,
}

# [EXE] atlas piece index of each floor type's background art.
FLOOR_PIECE: dict[FloorType, int] = {
    FloorType.GROUND: 12,
    FloorType.SECOND: 13,
    FloorType.BRICK_SHORT: 10,
    FloorType.BRICK_TALL: 11,
    FloorType.ROOF: 9,
}

# [EXE] atlas piece index of each cell kind.
CELL_PIECE: dict[CellKind, int] = {
    CellKind.PLAIN: 16,
    CellKind.DOOR: 2,
    CellKind.ARCHED: 6,
    CellKind.PEDIMENT_A: 14,
    CellKind.PEDIMENT_B: 15,
}

# [EXE] FUN_00405550: the cell type of each window slot, left to right, per
# floor type (FUN_00404ea0 picks the piece: type 0 -> 16, 1 -> door 2,
# 2 -> arched 6, 3 -> 14, 4 -> 15). Stone floors are 0,0,1|2,0,0; both brick
# floor types are 3,3,4,3,3. The roof has no cells.
_STONE_SIDE = CellKind.PLAIN
_BRICK_SIDE = CellKind.PEDIMENT_A
FLOOR_CELL_KINDS: dict[FloorType, tuple[CellKind, ...]] = {
    FloorType.GROUND: (_STONE_SIDE, _STONE_SIDE, CellKind.DOOR, _STONE_SIDE, _STONE_SIDE),
    FloorType.SECOND: (_STONE_SIDE, _STONE_SIDE, CellKind.ARCHED, _STONE_SIDE, _STONE_SIDE),
    FloorType.BRICK_SHORT: (_BRICK_SIDE, _BRICK_SIDE, CellKind.PEDIMENT_B, _BRICK_SIDE, _BRICK_SIDE),
    FloorType.BRICK_TALL: (_BRICK_SIDE, _BRICK_SIDE, CellKind.PEDIMENT_B, _BRICK_SIDE, _BRICK_SIDE),
}

# [EXE] cell origin x per window slot. Stone floors are taken verbatim.
# Brick center is [USER]/[ATLAS]-corrected from the exe's 104: the exe stores it
# as an 8px tile origin and its draw offset is register-passed and unknown.
# The brick strip's pilasters sit at world x 101-103 and 138-140, which puts the
# center bay's midpoint at 120, so the 24px window must start at 108. The user
# saw 104 as visibly off-center at the 2026-10-21 render checkpoint.
_STONE_COLUMN_X = (40, 72, 96, 144, 176)
_BRICK_COLUMN_X = (40, 72, 108, 144, 176)
COLUMN_X: dict[FloorType, tuple[int, ...]] = {
    FloorType.GROUND: _STONE_COLUMN_X,
    FloorType.SECOND: _STONE_COLUMN_X,
    FloorType.BRICK_SHORT: _BRICK_COLUMN_X,
    FloorType.BRICK_TALL: _BRICK_COLUMN_X,
}


@dataclass(frozen=True)
class LevelConfig:
    """Counts that scale with level difficulty."""
    floor_count: int
    section_count: int
    bird_pairs: int
    sill_obstacles: int
    drop_hazards: int


# [EXE] FUN_00409610 reads config table 0x419d78, indexed by level (1..10).
_LEVEL_TABLE: dict[int, LevelConfig] = {
    1: LevelConfig(9, 2, 0, 0, 0),
    2: LevelConfig(9, 2, 0, 0, 0),
    3: LevelConfig(13, 3, 0, 2, 0),
    4: LevelConfig(13, 3, 1, 2, 0),
    5: LevelConfig(17, 4, 1, 3, 1),
    6: LevelConfig(17, 4, 2, 4, 1),
    7: LevelConfig(17, 4, 2, 4, 2),
    8: LevelConfig(17, 4, 2, 4, 2),
    9: LevelConfig(17, 4, 2, 4, 3),
    10: LevelConfig(17, 4, 2, 4, 3),
}

_BOTTOM_FLOORS = (FloorType.GROUND, FloorType.SECOND)
_BRICK_PAIR = (FloorType.BRICK_SHORT, FloorType.BRICK_TALL)
_TOP_FLOORS = (FloorType.BRICK_SHORT, FloorType.BRICK_SHORT, FloorType.ROOF)

# [EXE] floor-type sequences, bottom to top, keyed by floor_count.
_FLOOR_SEQUENCES: dict[int, tuple[FloorType, ...]] = {
    9: _BOTTOM_FLOORS
    + (FloorType.BRICK_SHORT, FloorType.BRICK_TALL, FloorType.BRICK_SHORT,
       FloorType.BRICK_TALL, FloorType.BRICK_SHORT, FloorType.BRICK_SHORT,
       FloorType.ROOF),
    13: _BOTTOM_FLOORS + _BRICK_PAIR * 4 + _TOP_FLOORS,
    17: _BOTTOM_FLOORS + _BRICK_PAIR * 6 + _TOP_FLOORS,
}


def get_level_config(level: int) -> LevelConfig:
    """Return the configuration for a 1-based level, capped at level 10.

    Raises ValueError for levels below 1.
    """
    if level < 1:
        raise ValueError(f"level must be >= 1, got {level}")
    return _LEVEL_TABLE[min(level, MAX_CONFIGURED_LEVEL)]


def get_floor_sequence(level: int) -> tuple[FloorType, ...]:
    """Return the floor types for a level, bottom to top, ending in the roof."""
    return _FLOOR_SEQUENCES[get_level_config(level).floor_count]
