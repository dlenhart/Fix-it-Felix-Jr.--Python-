import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from entities.building import Building  # noqa: E402
from level_config import CELL_PIECE, CellKind, FloorType  # noqa: E402


def test_level_one_layout():
    b = Building(1, random.Random(0))
    assert len(b.floors) == 9 and b.section_count == 2
    assert b.floors[0].bottom_y == 320 and b.floors[0].height == 56
    assert b.floors[1].bottom_y == 264
    assert [c.kind for c in b.floors[0].cells][2] == CellKind.DOOR
    assert b.floors[8].cells == []


def test_fix_scores_100_then_500_for_last():
    b = Building(1, random.Random(0))
    first, second = b.cell(0, 0), b.cell(1, 4)
    b.damage(first, is_heavy=True)
    b.damage(second, is_heavy=False)
    assert b.broken_count == 2
    assert b.fix(first) == 100
    assert b.fix(second) == 500
    assert b.is_section_clear()


def test_fix_intact_window_scores_nothing():
    b = Building(1, random.Random(0))
    assert b.fix(b.cell(0, 0)) == 0


def test_arched_window_ignores_damage():
    b = Building(1, random.Random(0))
    arched = b.cell(1, 2)
    b.damage(arched, is_heavy=True)
    assert not arched.is_broken


def test_broken_count_only_counts_active_section():
    b = Building(1, random.Random(0))
    b.damage(b.section_floors(1)[0].cells[0], is_heavy=True)
    assert b.broken_count == 0


def test_scroll_target_and_ledge():
    b = Building(1, random.Random(0))
    assert b.scroll_target(0) == 0
    assert b.scroll_target(1) == sum(f.height for f in b.floors[:4])
    assert b.ledge_y(0) == b.floors[3].top_y


def test_advance_past_last_section_raises():
    b = Building(1, random.Random(0))
    b.advance_section()
    with pytest.raises(RuntimeError):
        b.advance_section()


def test_door_damage_and_floor_lookup():
    b = Building(1, random.Random(0))
    door = b.cell(0, 2)
    b.damage(door, is_heavy=True)
    assert door.door_damage == 5 and door.is_broken
    assert b.floor_at_y(300) is b.floors[0]
    assert b.floor_at_y(320) is None


class RecordingSound:
    def __init__(self):
        self.played = []

    def play_sfx(self, name):
        self.played.append(name)


def test_damage_plays_window_break_only_when_an_intact_window_breaks():
    b = Building(1, random.Random(0))
    sound = RecordingSound()
    cell = b.cell(1, 0)
    b.damage(cell, is_heavy=False, sound=sound)
    assert sound.played == ["window_break"]
    b.damage(cell, is_heavy=True, sound=sound)
    assert sound.played == ["window_break"]
    b.damage(b.cell(1, 2), is_heavy=True, sound=sound)  # arched: never damaged
    assert sound.played == ["window_break"]


def test_exe_sill_row_and_bounds():
    b = Building(5, random.Random(0))
    ground, second, brick = b.section_floors()[:3]
    pane = ground.cells[0]
    # FUN_00404ea0: pane sill at piece top + 0x24, bounds X*8 .. X*8+0x17.
    assert b.sill_y(pane) == ground.bottom_y - 48 + 36
    assert b.sill_span_x(pane) == (40, 63)
    assert b.sill_y(ground.cells[2]) == 0x138  # the door's piece top is the exe's (y 256)
    # The arched sill is the exe's row 37 of the piece, on our piece, drawn 8 px lower.
    assert b.sill_y(second.cells[2]) == 0xFD + 8
    assert b.sill_y(brick.cells[0]) == brick.bottom_y - 48 + 36
    assert b.sill_span_x(ground.cells[2]) == (100, 139)
    # Type 4 cell: exe stores X*8+4 .. X*8+0x1b with X*8 = 104, and draws the piece at 108.
    assert b.sill_span_x(brick.cells[2]) == (108, 131)


def test_brick_floors_use_the_exe_cell_types():
    # FUN_00405550: brick floors are types 3,3,4,3,3 (pieces 14,14,15,14,14);
    # stone floors 0,0,1|2,0,0 (pieces 16,16,door|arched,16,16).
    b = Building(5, random.Random(0))
    for floor in b.floors:
        pieces = [CELL_PIECE[cell.kind] for cell in floor.cells]
        if floor.floor_type in (FloorType.BRICK_SHORT, FloorType.BRICK_TALL):
            assert pieces == [14, 14, 15, 14, 14]
        elif floor.floor_type == FloorType.GROUND:
            assert pieces == [16, 16, 2, 16, 16]
        elif floor.floor_type == FloorType.SECOND:
            assert pieces == [16, 16, 6, 16, 16]
        else:
            assert pieces == []


def test_sill_obstacle_node_rests_on_the_sill_at_the_bounds_middle():
    b = Building(5, random.Random(0))
    brick = b.section_floors()[2]
    side, center = brick.cells[0], brick.cells[2]
    assert b.sill_middle_x(side) == side.x + 11  # (0x17 - 0) // 2
    assert b.sill_middle_x(center) == 108 + 11  # type 4 bounds 108..131
    assert b.sill_obstacle_node(side) == (side.x + 11, b.sill_y(side))
