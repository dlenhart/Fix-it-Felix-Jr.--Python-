import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
from random import Random

import pygame
pygame.init()

from entities.felix import Felix, FelixState
from entities.building import Building
from input_handler import Action
from constants import (
    BONUS_LIFE_THRESHOLD, INVULNERABLE_TICKS, FELIX_MAX_HORIZONTAL_SPEED,
    FELIX_STUN_START_BELOW, INITIAL_LIVES,
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


def test_place_at_anchors_on_cell_center_and_floor_bottom():
    f, b = make_felix(1, 3)
    x, y = f.world_pos()
    assert x == b.cell(1, 3).center_x
    assert y == b.section_floors()[1].bottom_y


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
    assert f.world_pos() == (b.cell(1, 2).center_x, b.section_floors()[1].bottom_y)


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


def test_hit_costs_life_and_stuns():
    f, b = make_felix()
    assert f.hit() is True
    assert f.state == FelixState.STUNNED
    assert f.lives == INITIAL_LIVES - 1


def test_hit_ignored_while_stunned():
    f, b = make_felix()
    f.hit()
    assert f.hit() is False
    assert f.lives == INITIAL_LIVES - 1


def test_stun_drops_below_anchor_then_recovers():
    f, b = make_felix()
    f.hit()
    tick_n(f, b, 1)
    _, feet_y = f.world_pos()
    assert feet_y == b.section_floors()[0].bottom_y + FELIX_STUN_START_BELOW
    tick_n(f, b, 600)
    assert f.state == FelixState.IDLE
    assert f.world_pos()[1] == b.section_floors()[0].bottom_y


def test_final_hit_leads_to_dying():
    f, b = make_felix()
    f.lives = 1
    f.hit()
    tick_n(f, b, 600)
    assert f.lives == 0
    assert f.state in (FelixState.DYING, FelixState.DEATH_HANDLER)


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
