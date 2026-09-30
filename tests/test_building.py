import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from entities.building import WindowSlot, WindowState, Building


def test_window_damage_cycle():
    w = WindowSlot()
    assert w.state == WindowState.INTACT
    w.damage()
    assert w.state == WindowState.CRACKED
    w.damage()
    assert w.state == WindowState.BROKEN
    w.damage()
    assert w.state == WindowState.BROKEN


def test_window_repair_cycle():
    w = WindowSlot()
    w.state = WindowState.BROKEN
    repaired, fully_fixed = w.repair()
    assert repaired is True
    assert fully_fixed is False
    assert w.state == WindowState.CRACKED
    repaired, fully_fixed = w.repair()
    assert repaired is True
    assert fully_fixed is True
    assert w.state == WindowState.INTACT


def test_window_repair_intact_noop():
    w = WindowSlot()
    repaired, fully_fixed = w.repair()
    assert repaired is False
    assert fully_fixed is False


def test_window_super_repair():
    w = WindowSlot()
    w.state = WindowState.BROKEN
    repaired, fully_fixed = w.repair(is_super=True)
    assert repaired is True
    assert fully_fixed is True
    assert w.state == WindowState.INTACT


def test_section_clear():
    b = Building()
    b.reset_for_level(1)
    assert not b.is_section_clear()
    for row in b._current_grid:
        for window in row:
            window.state = WindowState.INTACT
    assert b.is_section_clear()


def test_level_progression():
    b = Building()
    b.reset_for_level(1)
    for _ in range(SECTIONS_PER_LEVEL):
        for row in b._current_grid:
            for window in row:
                window.state = WindowState.INTACT
        b.advance_section()
    assert b.is_level_clear()


if __name__ == "__main__":
    from entities.building import SECTIONS_PER_LEVEL
    test_window_damage_cycle()
    test_window_repair_cycle()
    test_window_repair_intact_noop()
    test_window_super_repair()
    test_section_clear()
    test_level_progression()
    print("All building tests passed!")
