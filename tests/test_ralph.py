import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from entities.building import Building  # noqa: E402
from entities.ralph import Ralph, RalphState  # noqa: E402


def make_ralph(seed=0, level=5):
    building = Building(level, random.Random(seed))
    ralph = Ralph(random.Random(seed))
    ralph.place_on_ledge(building)
    return ralph, building


def test_place_on_ledge():
    ralph, building = make_ralph()
    assert (ralph.x, ralph.y, ralph.state) == (120, building.ledge_y(), RalphState.WALK)


def test_patrol_order_is_center_left_center_right():
    ralph, building = make_ralph()
    arrivals = []
    previous_state = ralph.state
    for _ in range(2000):
        ralph.tick(building, 5)
        if ralph.state == RalphState.POUND and previous_state == RalphState.WALK:
            arrivals.append(ralph.x)
        previous_state = ralph.state
    assert arrivals[:6] == [72, 120, 169, 120, 72, 120]


def collect_pound_spawn_ticks(ralph, building, tick_count):
    spawn_ticks = []
    spawn_positions = []
    for tick_number in range(tick_count):
        events = ralph.tick(building, 5)
        for position in events.brick_spawns:
            spawn_ticks.append(tick_number)
            spawn_positions.append((ralph.x, ralph.y, position))
    return spawn_ticks, spawn_positions


def test_pound_brick_interval_between_9_and_16_ticks():
    ralph, building = make_ralph()
    ralph.x = 72  # skip the walk: arrive immediately
    ralph._target_x = 72
    ralph.tick(building, 5)
    assert ralph.state == RalphState.POUND
    ticks = []
    for tick_number in range(59):
        if ralph.tick(building, 5).brick_spawns:
            ticks.append(tick_number)
    assert len(ticks) >= 3
    assert 9 <= ticks[0] + 1 <= 16
    assert all(9 <= later - earlier <= 16 for earlier, later in zip(ticks, ticks[1:]))


def test_brick_spawn_within_spread_of_ralph():
    ralph, building = make_ralph()
    _, positions = collect_pound_spawn_ticks(ralph, building, 3000)
    assert len(positions) > 20
    for ralph_x, ralph_y, (brick_x, brick_y) in positions:
        assert ralph_x - 32 <= brick_x <= ralph_x + 31
        assert brick_y == ralph_y + 8


def drop_requests(level):
    ralph, building = make_ralph(level=level)
    request_ticks = []
    for tick_number in range(3000):
        if ralph.tick(building, level).is_drop_hazard_requested:
            request_ticks.append(tick_number)
    return request_ticks


def test_drop_hazard_requested_after_three_cycles():
    request_ticks = drop_requests(5)
    assert len(request_ticks) >= 2
    assert request_ticks[1] - request_ticks[0] > 100


def test_drop_hazard_first_request_comes_after_third_pound_ends():
    ralph, building = make_ralph()
    cycles_seen = 0
    previous_state = ralph.state
    for _ in range(3000):
        events = ralph.tick(building, 5)
        if previous_state == RalphState.POUND and ralph.state == RalphState.WALK:
            cycles_seen += 1
        previous_state = ralph.state
        if events.is_drop_hazard_requested:
            break
    assert cycles_seen == 3


def test_no_drop_hazard_on_levels_without_them():
    assert drop_requests(1) == []


def test_rage_waits_80_then_brick_every_8_for_240():
    ralph, building = make_ralph()
    ralph.start_rage()
    spawn_ticks = []
    for tick_number in range(1, 320):  # stop before the post-rage patrol pounds
        if ralph.tick(building, 5).brick_spawns:
            spawn_ticks.append(tick_number)
    assert len(spawn_ticks) == 30
    assert spawn_ticks[0] == 80
    assert all(later - earlier == 8 for earlier, later in zip(spawn_ticks, spawn_ticks[1:]))
    ralph.tick(building, 5)
    assert ralph.state == RalphState.WALK


def test_rage_ignored_during_climb_and_section_pose():
    ralph, building = make_ralph()
    ralph.start_section_clear()
    ralph.start_rage()
    assert ralph.state == RalphState.SECTION_POSE
    ralph.start_climb(building, ralph.y)
    ralph.start_rage()
    assert ralph.state == RalphState.CLIMB


def test_section_pose_holds_until_climb():
    ralph, building = make_ralph()
    ralph.start_section_clear()
    for _ in range(500):
        ralph.tick(building, 5)
    assert ralph.state == RalphState.SECTION_POSE


def test_climb_reaches_new_ledge_and_damages_section():
    ralph, building = make_ralph(seed=1)
    old_y = building.ledge_y()
    building.advance_section()
    ralph.start_section_clear()
    ralph.start_climb(building, old_y)
    finished_ticks = None
    for tick_number in range(1, 2000):
        if ralph.tick(building, 5).is_climb_finished:
            finished_ticks = tick_number
            break
    assert finished_ticks is not None
    assert ralph.y == building.ledge_y() and ralph.x == 120
    assert ralph.state == RalphState.WALK
    assert building.broken_count > 0


def test_climb_slides_to_center_first_and_first_heavy_cell_is_hit():
    ralph, building = make_ralph()
    ralph.x = 72
    cell = building.cell(0, 0)
    ralph.start_climb(building, 320, first_heavy_cell=cell)
    assert cell.is_broken
    start_y = ralph.y
    for _ in range(10):
        ralph.tick(building, 5)
    assert ralph.x == 72 + 10 and ralph.y == start_y


def test_walk_after_climb_targets_left_first():
    ralph, building = make_ralph()
    building.advance_section()
    ralph.start_climb(building, building.ledge_y() + 5)
    for _ in range(10):
        ralph.tick(building, 5)
    assert ralph._target_x == 72
