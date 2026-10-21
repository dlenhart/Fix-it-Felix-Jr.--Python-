import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
from random import Random

import pygame
pygame.init()

from entities.felix import (
    Felix, FelixState, FELIX_HIT_FALL_GRAVITY, FELIX_RESPAWN_DELAY_TICKS,
    FELIX_GAME_OVER_DELAY_TICKS, HIT_ANIM_TICKS,
)
from entities.building import Building
from input_handler import Action
from level_config import STREET_Y, CellKind
from constants import (
    BONUS_LIFE_THRESHOLD, INVULNERABLE_TICKS, FELIX_MAX_HORIZONTAL_SPEED,
    INITIAL_LIVES,
)


class MockInput:
    def __init__(self, *actions):
        self._just = set(actions)

    def is_just_pressed(self, action):
        return action in self._just

    def is_pressed(self, action):
        return action in self._just


class RecordingSound:
    def __init__(self):
        self.played = []

    def play_sfx(self, name):
        self.played.append(name)


def make_felix(local_row=0, column=2):
    building = Building(1, Random(0))
    felix = Felix()
    felix.place_at(local_row, column, building)
    return felix, building


def tick_n(felix, building, count, sound=None):
    for _ in range(count):
        felix.tick(MockInput(), building, sound)


def press(felix, building, action, sound=None):
    felix.tick(MockInput(action), building, sound)


def swing(felix, building, sound=None):
    press(felix, building, Action.JUMP, sound)
    for _ in range(100):
        if felix.state == FelixState.IDLE:
            return
        tick_n(felix, building, 1, sound)
    raise AssertionError("swing never finished")


def test_initial_state():
    f = Felix()
    assert (f.column, f.local_row) == (2, 0)
    assert f.state == FelixState.IDLE
    assert f.lives == INITIAL_LIVES
    assert f.score == 0
    assert not f.is_invulnerable


def test_place_at_anchors_on_cell_center_and_sill():
    f, b = make_felix(1, 3)
    x, y = f.world_pos()
    assert x == b.cell(1, 3).center_x
    assert y == b.sill_y(b.cell(1, 3))


def test_feet_on_sill_for_every_cell_kind():
    b = Building(1, Random(0))
    for local_row in range(4):
        for column in range(5):
            f = Felix()
            f.place_at(local_row, column, b)
            assert f.world_pos()[1] == b.sill_y(b.cell(local_row, column))


def test_sill_y_measured_rise_above_floor_bottom():
    b = Building(1, Random(0))
    floor = b.section_floors()[0]
    assert b.sill_y(b.cell(0, 0)) == floor.bottom_y - 5  # pane window
    door = b.cell(0, 2)
    assert door.kind == CellKind.DOOR
    assert b.sill_y(door) == floor.bottom_y
    arched = b.cell(1, 2)
    assert arched.kind == CellKind.ARCHED
    assert b.sill_y(arched) == b.section_floors()[1].bottom_y


def test_hitbox_is_12_by_28_standing_on_feet():
    f, b = make_felix()
    x, y = f.world_pos()
    box = f.hitbox()
    assert (box.width, box.height) == (12, 28)
    assert box.centerx == round(x)
    assert box.bottom == y


def test_walk_accelerates_and_stops_on_next_cell():
    f, b = make_felix(0, 2)
    start_x, _ = f.world_pos()
    press(f, b, Action.RIGHT)
    assert f.state == FelixState.WALK_HORIZONTAL
    speeds = []
    previous_x = start_x
    for _ in range(200):
        if f.state != FelixState.WALK_HORIZONTAL:
            break
        tick_n(f, b, 1)
        x, _ = f.world_pos()
        speeds.append(x - previous_x)
        previous_x = x
    assert f.state == FelixState.IDLE
    assert speeds[0] < speeds[1] <= FELIX_MAX_HORIZONTAL_SPEED
    assert max(speeds) <= FELIX_MAX_HORIZONTAL_SPEED
    assert f.column == 3
    assert f.world_pos()[0] == b.cell(0, 3).center_x


def test_reverse_mid_walk_returns_to_start_cell():
    f, b = make_felix(0, 2)
    press(f, b, Action.RIGHT)
    tick_n(f, b, 3)
    press(f, b, Action.LEFT)
    assert not f.facing_right
    for _ in range(200):
        if f.state != FelixState.WALK_HORIZONTAL:
            break
        tick_n(f, b, 1)
    assert f.state == FelixState.IDLE
    assert f.column == 2
    assert f.world_pos()[0] == b.cell(0, 2).center_x


def test_walk_off_edges_refused():
    f, b = make_felix(0, 0)
    press(f, b, Action.LEFT)
    assert f.state == FelixState.IDLE
    f, b = make_felix(0, 4)
    press(f, b, Action.RIGHT)
    assert f.state == FelixState.IDLE


def test_up_moves_to_next_floor():
    f, b = make_felix(0, 2)
    press(f, b, Action.UP)
    assert f.state == FelixState.JUMPING
    tick_n(f, b, 200)
    assert f.state == FelixState.IDLE
    assert f.local_row == 1
    assert f.world_pos() == (b.cell(1, 2).center_x, b.sill_y(b.cell(1, 2)))


def test_up_blocked_by_sill_obstacle():
    f, b = make_felix(0, 2)
    b.cell(0, 2).has_sill_obstacle = True
    press(f, b, Action.UP)
    assert f.state == FelixState.IDLE
    assert f.local_row == 0


def test_up_blocked_on_top_floor_and_down_on_bottom():
    f, b = make_felix(3, 2)
    press(f, b, Action.UP)
    assert f.state == FelixState.IDLE
    f, b = make_felix(0, 2)
    press(f, b, Action.DOWN)
    assert f.state == FelixState.IDLE


def test_one_swing_fixes_window_and_scores_100():
    f, b = make_felix(0, 1)
    b.damage(b.cell(0, 1), is_heavy=True)
    b.damage(b.cell(1, 1), is_heavy=True)  # keeps the section from clearing
    sound = RecordingSound()
    swing(f, b, sound)
    assert not b.cell(0, 1).is_broken
    assert f.score == 100
    assert "hammer_hit" in sound.played
    assert "window_fixed" not in sound.played


def test_last_window_scores_500_and_flags_last_fixed_points():
    f, b = make_felix(0, 1)
    b.damage(b.cell(0, 1), is_heavy=True)
    sound = RecordingSound()
    press(f, b, Action.JUMP, sound)
    seen = []
    for _ in range(100):
        tick_n(f, b, 1, sound)
        seen.append(f.last_fixed_points)
        if f.state == FelixState.IDLE:
            break
    assert f.score == 500
    assert 500 in seen
    tick_n(f, b, 1)
    assert f.last_fixed_points == 0  # reset at the start of the next tick
    assert "window_fixed" in sound.played


def test_swing_at_intact_window_scores_nothing():
    f, b = make_felix(0, 1)
    swing(f, b)
    assert f.score == 0
    assert f.last_fixed_points == 0


def test_bonus_life_every_5000():
    f = Felix()
    f.add_score(5000)
    assert f.lives == INITIAL_LIVES + 1
    f.add_score(4999)
    assert f.lives == INITIAL_LIVES + 1
    f.add_score(1)
    assert f.lives == INITIAL_LIVES + 2
    assert BONUS_LIFE_THRESHOLD == 5000


def test_hit_starts_sequence_without_losing_a_life_yet():
    f, b = make_felix()
    assert f.hit() is True
    assert f.state == FelixState.HIT_ANIM
    assert f.is_in_hit_sequence
    assert f.lives == INITIAL_LIVES


def test_hit_ignored_during_sequence():
    f, b = make_felix()
    f.hit()
    assert f.hit() is False
    tick_n(f, b, HIT_ANIM_TICKS + 5)
    assert f.state == FelixState.HIT_FALL
    assert f.hit() is False
    assert f.lives == INITIAL_LIVES


def test_hit_animation_plays_in_place_then_falls_with_exe_gravity():
    f, b = make_felix(1, 3)
    start = f.world_pos()
    f.hit()
    for _ in range(HIT_ANIM_TICKS - 1):
        tick_n(f, b, 1)
        assert f.state == FelixState.HIT_ANIM
        assert f.world_pos() == start
    tick_n(f, b, 1)
    assert f.state == FelixState.HIT_FALL
    assert f.world_pos() == start
    positions = []
    for _ in range(4):
        tick_n(f, b, 1)
        positions.append(f.world_pos()[1])
    steps = [positions[0] - start[1]] + [b2 - a for a, b2 in zip(positions, positions[1:])]
    for index, step in enumerate(steps):
        assert abs(step - FELIX_HIT_FALL_GRAVITY * (index + 1)) < 1e-9
    assert f.world_pos()[0] == start[0]


def test_hit_animation_frame_ids_follow_facing():
    f, b = make_felix()
    f.facing_right = True
    f.hit()
    assert f._hit_frame_id() == 34
    tick_n(f, b, 6)
    assert f._hit_frame_id() == 35
    f, b = make_felix()
    f.facing_right = False
    f.hit()
    assert f._hit_frame_id() == 64


def fall_off(felix, building):
    for _ in range(2000):
        if felix.state == FelixState.HIT_RESPAWN_WAIT:
            return
        tick_n(felix, building, 1)
    raise AssertionError("Felix never fell off")


def test_falls_past_street_then_waits_60_hidden_then_respawns_same_cell():
    f, b = make_felix(2, 4)
    f.hit()
    fall_off(f, b)
    assert f.world_pos()[1] > STREET_Y + 40
    assert f.lives == INITIAL_LIVES
    for _ in range(FELIX_RESPAWN_DELAY_TICKS - 1):
        tick_n(f, b, 1)
        assert f.state == FelixState.HIT_RESPAWN_WAIT
    assert f.lives == INITIAL_LIVES
    tick_n(f, b, 1)
    assert f.state == FelixState.IDLE
    assert not f.is_in_hit_sequence
    assert f.lives == INITIAL_LIVES - 1
    assert (f.local_row, f.column) == (2, 4)
    assert f.world_pos() == (b.cell(2, 4).center_x, b.sill_y(b.cell(2, 4)))


def test_hit_mid_walk_respawns_on_the_cell_he_left():
    f, b = make_felix(0, 2)
    press(f, b, Action.RIGHT)
    tick_n(f, b, 3)
    f.hit()
    fall_off(f, b)
    tick_n(f, b, FELIX_RESPAWN_DELAY_TICKS)
    assert (f.local_row, f.column) == (0, 2)


def test_last_life_never_respawns_and_ends_in_game_over():
    f, b = make_felix(1, 1)
    f.lives = 1
    sound = RecordingSound()
    start = f.world_pos()
    assert f.hit(sound) is True
    assert f.state == FelixState.FINAL_HIT_ANIM
    assert sound.played == ["death"]
    states = set()
    for _ in range(5000):
        if f.is_game_over:
            break
        tick_n(f, b, 1, sound)
        states.add(f.state)
        if not f.is_game_over:
            assert f.world_pos() == start  # the final sequence stays on the sill
            assert f.lives == 1
    assert f.is_game_over
    assert FelixState.IDLE not in states
    assert FelixState.HIT_FALL not in states
    assert f.lives == 0
    assert sound.played == ["death"]
    tick_n(f, b, 500)
    assert f.is_game_over
    assert f.lives == 0


def test_final_sequence_timing_from_exe_holds():
    f, b = make_felix()
    f.lives = 1
    f.hit()
    # Frame index 7 is reached after frames 0-6 show for hold + 1 ticks each.
    settle_ticks = 31 + 6 * 13
    tick_n(f, b, settle_ticks - 1)
    assert f.state == FelixState.FINAL_HIT_ANIM
    tick_n(f, b, 1)
    assert f.state == FelixState.FINAL_HIT_HOLD
    assert f._hit_frame_id() == 72
    tick_n(f, b, FELIX_GAME_OVER_DELAY_TICKS - 1)
    assert not f.is_game_over
    assert f._hit_frame_id() == 74  # lies on the halo frame
    tick_n(f, b, 1)
    assert f.is_game_over


def test_invulnerable_ignores_hit_and_expires_after_480_ticks():
    f, b = make_felix()
    sound = RecordingSound()
    f.activate_invulnerability(sound)
    assert "super_felix" in sound.played
    assert f.is_invulnerable
    assert f.hit() is False
    assert f.lives == INITIAL_LIVES
    tick_n(f, b, INVULNERABLE_TICKS - 1)
    assert f.is_invulnerable
    tick_n(f, b, 1)
    assert not f.is_invulnerable
    assert f.hit() is True
