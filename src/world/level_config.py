"""Per-level lookups over the exe level table. No pygame dependency."""

from constants.levels import MAX_CONFIGURED_LEVEL
from exe_data.level_table import FLOOR_SEQUENCES, LEVEL_TABLE
from world.level_types import FloorType, LevelConfig


def get_level_config(level: int) -> LevelConfig:
    """Return the configuration for a 1-based level, capped at level 10.

    Raises ValueError for levels below 1.
    """
    if level < 1:
        raise ValueError(f"level must be >= 1, got {level}")
    return LEVEL_TABLE[min(level, MAX_CONFIGURED_LEVEL)]


def get_floor_sequence(level: int) -> tuple[FloorType, ...]:
    """Return the floor types for a level, bottom to top, ending in the roof.

    Raises LookupError when the level table names a floor count with no sequence.
    """
    floor_count = get_level_config(level).floor_count
    if floor_count not in FLOOR_SEQUENCES:
        raise LookupError(f"level {level}: no floor sequence for floor_count {floor_count}")
    return FLOOR_SEQUENCES[floor_count]
