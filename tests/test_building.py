import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from entities.building import Building  # noqa: E402
from level_config import CellKind  # noqa: E402


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
