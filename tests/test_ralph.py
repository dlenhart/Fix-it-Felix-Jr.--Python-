import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from entities.building import Building  # noqa: E402
from entities.ralph import DropHazardSchedule, Ralph, RalphState  # noqa: E402


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


def arrive_at_pound(ralph, building, level=5):
    """Put Ralph on his walk target so this tick is the arrival (FUN_0040d870); returns its events."""
    ralph._target_x = ralph.x
    events = ralph.tick(building, level)
    assert ralph.state == RalphState.POUND
    return events


def test_pound_winds_up_then_drops_bricks_every_9_to_16_ticks_and_lasts_76():
    # FUN_0040d870 sets the countdown to 9; FUN_0040d970 only counts it after the
    # 20-tick wind-up (anim 24 frames 0-1), then re-rolls 9 + rand() & 7.
    ralph, building = make_ralph()
    arrive_at_pound(ralph, building)
    spawn_ticks = []
    tick_number = 0
    while ralph.state == RalphState.POUND:
        tick_number += 1
        if ralph.tick(building, 5).brick_spawns:
            spawn_ticks.append(tick_number)
    assert tick_number == 76  # the walk starts on the tick anim 24 is seen finished
    assert spawn_ticks[0] == 20 + 9
    assert all(9 <= later - earlier <= 16 for earlier, later in zip(spawn_ticks, spawn_ticks[1:]))


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


def test_drop_hazard_comes_30_ticks_into_the_third_pounds_main_phase():
    ralph, building = make_ralph()
    arrivals = 0
    ticks_since_arrival = 0
    previous_state = ralph.state
    for _ in range(3000):
        events = ralph.tick(building, 5)
        ticks_since_arrival += 1
        if previous_state == RalphState.WALK and ralph.state == RalphState.POUND:
            arrivals += 1
            ticks_since_arrival = 0
        previous_state = ralph.state
        if events.is_drop_hazard_requested:
            break
    assert arrivals == 3
    assert ralph.state == RalphState.POUND
    assert ticks_since_arrival == 20 + 30


def test_drop_schedule_carries_over_to_the_next_levels_ralph():
    schedule = DropHazardSchedule()
    building = Building(5, random.Random(0))
    for _ in range(2):
        ralph = Ralph(random.Random(0), schedule)
        ralph.place_on_ledge(building)
        arrive_at_pound(ralph, building)
    next_ralph = Ralph(random.Random(0), schedule)
    next_ralph.place_on_ledge(building)
    arrive_at_pound(next_ralph, building)
    requests = [next_ralph.tick(building, 5).is_drop_hazard_requested for _ in range(76)]
    assert requests.index(True) == 20 + 30 - 1


def test_armed_drop_timer_only_counts_while_pounding():
    schedule = DropHazardSchedule()
    for _ in range(3):
        schedule.on_pound_arrival()
    ralph = Ralph(random.Random(0), schedule)
    building = Building(5, random.Random(0))
    ralph.place_on_ledge(building)
    ralph.start_section_clear()  # the pre-roof wait: Ralph poses
    assert not any(ralph.tick(building, 5).is_drop_hazard_requested for _ in range(500))
    assert [schedule.tick_pound() for _ in range(30)] == [False] * 29 + [True]


def test_drop_schedule_arms_on_every_third_arrival():
    schedule = DropHazardSchedule()
    fired = []
    for _ in range(6):
        schedule.on_pound_arrival()
        fired.append(any(schedule.tick_pound() for _ in range(30)))
    assert fired == [False, False, True, False, False, True]


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
    assert ralph.state == RalphState.IDLE  # FUN_0040dbb0 leaves him on the ledge until play resumes
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


class RecordingSound:
    def __init__(self):
        self.played = []

    def play_sfx(self, name):
        self.played.append(name)


class AlwaysDamageRandom(random.Random):
    """Every climb damage roll succeeds (FUN_0040dbb0's 50% roll)."""

    def random(self):
        return 0.0


def climb_with_sound(building, sound, first_heavy_cell=None):
    ralph = Ralph(AlwaysDamageRandom(0))
    old_y = building.ledge_y()
    building.advance_section()
    ralph.start_climb(building, old_y, first_heavy_cell=first_heavy_cell, sound=sound)
    for _ in range(2000):
        if ralph.tick(building, 5, sound).is_climb_finished:
            return
    raise AssertionError("climb never finished")


def section_damageable_cells(building):
    return [cell for floor in building.section_floors() for cell in floor.cells
            if cell.is_damageable]


def test_climb_damage_plays_window_break_once_per_intact_window():
    building = Building(5, random.Random(0))
    sound = RecordingSound()
    climb_with_sound(building, sound)
    broken_count = building.broken_count
    assert broken_count > 0
    assert sound.played.count("window_break") == broken_count


def test_climb_damage_on_broken_windows_is_silent():
    building = Building(5, random.Random(0))
    building.advance_section()
    for cell in section_damageable_cells(building):
        building.damage(cell, is_heavy=True)
    building.section_index = 0
    sound = RecordingSound()
    climb_with_sound(building, sound)
    assert "window_break" not in sound.played


def test_level_start_heavy_hit_plays_window_break():
    building = Building(5, random.Random(0))
    sound = RecordingSound()
    door = building.cell(0, 2)
    Ralph(random.Random(0)).start_climb(building, 320, first_heavy_cell=door, sound=sound)
    assert door.is_broken
    assert sound.played == ["window_break"]


class SmashSoundRecorder:
    def __init__(self):
        self.restarted = []

    def restart_sound_index(self, index):
        self.restarted.append(index)

    def play_sfx(self, name):
        pass


def test_pound_smash_sound_on_frames_82_and_84():
    # FUN_0040d970: sound 0x10 restarts when the node lands on frame 0x52 or 0x54;
    # anim 24 reaches them at ticks 20, 34, 48 and 62 after the arrival.
    ralph, building = make_ralph()
    arrive_at_pound(ralph, building)
    sound = SmashSoundRecorder()
    smash_ticks = []
    for tick_number in range(1, 77):
        before = len(sound.restarted)
        ralph.tick(building, 5, sound)
        if len(sound.restarted) > before:
            smash_ticks.append(tick_number)
    assert smash_ticks == [20, 34, 48, 62]
    assert set(sound.restarted) == {0x10}


def test_rage_smash_sound_on_every_frame_of_anim_25():
    ralph, building = make_ralph()
    ralph.start_rage()
    sound = SmashSoundRecorder()
    smash_ticks = []
    for tick_number in range(1, 200):
        before = len(sound.restarted)
        ralph.tick(building, 5, sound)
        if len(sound.restarted) > before:
            smash_ticks.append(tick_number)
    assert smash_ticks[0] > 80  # nothing during the wind-up (anim 26)
    assert all(later - earlier == 7 for earlier, later in zip(smash_ticks, smash_ticks[1:]))


def test_frames_follow_the_exe_animations():
    ralph, building = make_ralph()
    assert ralph.frame_id in (78, 79)  # walking, anim 23
    arrive_at_pound(ralph, building)
    shown = set()
    while ralph.state == RalphState.POUND:
        shown.add(ralph.frame_id)
        ralph.tick(building, 5)
    assert shown == set(range(80, 86))  # anim 24
    ralph.start_climb(building, ralph.y + 40)
    assert ralph.frame_id in (88, 89)  # anim 27
    ralph.start_section_clear(is_last_section=True)
    assert ralph.frame_id == 75  # anim 20
    ralph.start_section_clear(is_last_section=False)
    assert ralph.frame_id in (80, 81)  # anim 26


def test_idle_on_the_ledge_keeps_animating():
    ralph, building = make_ralph()
    ralph.idle()
    shown = set()
    for _ in range(30):
        ralph.animate()
        shown.add(ralph.frame_id)
    assert shown == {80, 81}


def walk_to_next_pound(ralph, building):
    while ralph.state != RalphState.WALK:
        ralph.tick(building, 5)
    for _ in range(500):
        ralph.tick(building, 5)
        if ralph.state == RalphState.POUND:
            return
    raise AssertionError("Ralph never reached a pound spot")


def next_walk_target(ralph, building):
    """Walk until Ralph arrives somewhere and return where."""
    walk_to_next_pound(ralph, building)
    return ralph.x


def test_respawn_restart_from_a_side_heads_back_to_center():
    ralph, building = make_ralph()
    walk_to_next_pound(ralph, building)
    assert ralph.x == 72
    ralph.restart_patrol()
    assert ralph.state == RalphState.WALK
    assert next_walk_target(ralph, building) == 120


def test_respawn_restart_from_center_always_heads_for_72():
    # FUN_0040e220 clears +0xe2e, so even a patrol due to go right turns left.
    ralph, building = make_ralph()
    walk_to_next_pound(ralph, building)  # 72
    walk_to_next_pound(ralph, building)  # 120, next out would be 169
    assert ralph.x == 120
    ralph.restart_patrol()
    assert next_walk_target(ralph, building) == 72


def test_respawn_restart_mid_walk_out_turns_for_72():
    ralph, building = make_ralph()
    walk_to_next_pound(ralph, building)  # 72
    walk_to_next_pound(ralph, building)  # 120
    while ralph.state != RalphState.WALK:
        ralph.tick(building, 5)
    ralph.tick(building, 5)
    assert ralph.x > 120  # on the way out to 169
    ralph.restart_patrol()
    assert next_walk_target(ralph, building) == 72
