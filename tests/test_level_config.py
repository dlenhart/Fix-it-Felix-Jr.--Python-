import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from level_config import (  # noqa: E402
    COLUMN_X,
    FLOORS_PER_SECTION,
    FloorType,
    LevelConfig,
    get_floor_sequence,
    get_level_config,
)


def test_level_table_rows():
    assert get_level_config(1) == LevelConfig(9, 2, 0, 0, 0)
    assert get_level_config(4) == LevelConfig(13, 3, 1, 2, 0)
    assert get_level_config(6) == LevelConfig(17, 4, 2, 4, 1)
    assert get_level_config(9) == LevelConfig(17, 4, 2, 4, 3)


def test_levels_past_ten_use_level_ten():
    assert get_level_config(11) == get_level_config(10)
    assert get_level_config(50) == get_level_config(10)


def test_floor_sequence_matches_floor_count_and_ends_with_roof():
    for level in range(1, 12):
        sequence = get_floor_sequence(level)
        assert len(sequence) == get_level_config(level).floor_count
        assert sequence[0] == FloorType.GROUND and sequence[1] == FloorType.SECOND
        assert sequence[-1] == FloorType.ROOF
        assert len(sequence) - 1 == get_level_config(level).section_count * FLOORS_PER_SECTION


def test_floor_sequences_match_spec():
    B, T = FloorType.BRICK_SHORT, FloorType.BRICK_TALL
    assert get_floor_sequence(1)[2:-1] == (B, T, B, T, B, B)
    assert get_floor_sequence(3)[2:-1] == (B, T) * 4 + (B, B)
    assert get_floor_sequence(5)[2:-1] == (B, T) * 6 + (B, B)


def test_center_cell_is_centered_on_x_120():
    BUILDING_CENTER_X = 120
    CENTER_CELL_WIDTH_BRICK = 24
    CENTER_CELL_WIDTH_STONE = 48
    for floor_type, column_x in COLUMN_X.items():
        center_cell_width = (
            CENTER_CELL_WIDTH_BRICK
            if floor_type in (FloorType.BRICK_SHORT, FloorType.BRICK_TALL)
            else CENTER_CELL_WIDTH_STONE
        )
        assert column_x[2] + center_cell_width / 2 == BUILDING_CENTER_X


def test_level_zero_raises():
    with pytest.raises(ValueError):
        get_level_config(0)
