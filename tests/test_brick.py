import os
import random
import sys

import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from constants import (  # noqa: E402
    BRICK_BOUNCE_TICKS, BRICK_FALL_SPEED, BRICK_MAX_LIVE, BRICK_WINDOW_BREAKS_PER_SECTION,
    GROUND_Y,
)
from entities.brick import BRICK_WIDTH, Brick, BrickField  # noqa: E402
from entities.building import Building  # noqa: E402
from entities.felix import HITBOX_HEIGHT, HITBOX_WIDTH, Felix  # noqa: E402


class AlwaysNinetyNineRandom:
    def randrange(self, stop):
        return 99

    def random(self):
        return 0.0


def make_world(level=1, seed=0):
    building = Building(level, random.Random(seed))
    felix = Felix()
    felix.place_at(0, 0, building)
    return building, felix


def spawn_on_felix(field, felix):
    hitbox = felix.hitbox()
    field.spawn(hitbox.centerx, hitbox.centery)


def upper_window_cells(building):
    return [cell for floor in building.section_floors()[1:] for cell in floor.cells
            if cell.is_damageable]


def spawn_in_glass(field, building, cell):
    glass = building.glass_rect(cell)
    field.spawn(glass.centerx, glass.centery + 12)


def test_brick_falls_1_9_per_tick():
    building, felix = make_world()
    brick = Brick(100, 0)
    brick.tick_fall()
    assert brick.y == BRICK_FALL_SPEED == 1.9
    assert brick.x == 100
    assert brick.rect().bottom == 2


def test_brick_hits_felix_once_and_vanishes():
    building, felix = make_world()
    field = BrickField(random.Random(0))
    lives = felix.lives
    spawn_on_felix(field, felix)
    assert field.tick(building, felix, level=1) is True
    assert felix.is_in_hit_sequence
    assert felix.lives == lives  # the life is lost at the respawn (FUN_0040c1a0)
    assert field.live_count == 0
    assert field.tick(building, felix, level=1) is False


def test_brick_vanishes_on_felix_in_hit_sequence_without_second_hit():
    building, felix = make_world()
    field = BrickField(random.Random(0))
    spawn_on_felix(field, felix)
    field.tick(building, felix, level=1)
    lives = felix.lives
    spawn_on_felix(field, felix)
    assert field.tick(building, felix, level=1) is False
    assert felix.lives == lives
    assert field.live_count == 0


def test_invulnerable_felix_bounces_brick_and_keeps_lives():
    building, felix = make_world()
    felix.activate_invulnerability()
    field = BrickField(random.Random(0))
    lives = felix.lives
    spawn_on_felix(field, felix)
    assert field.tick(building, felix, level=1) is False
    assert felix.lives == lives
    assert field.live_count == 1
    assert field._bricks[0].is_bouncing


def test_level_one_bricks_never_break_windows():
    building, felix = make_world(level=1)
    field = BrickField(random.Random(1))
    cell = upper_window_cells(building)[0]
    for _ in range(10_000):
        field.clear()
        spawn_in_glass(field, building, cell)
        field.tick(building, felix, level=1)
    assert not cell.is_broken


def test_window_break_budget_caps_at_four_per_section():
    building, felix = make_world(level=2)
    field = BrickField(AlwaysNinetyNineRandom())
    cells = upper_window_cells(building)
    assert len(cells) > BRICK_WINDOW_BREAKS_PER_SECTION + 1
    for cell in cells:
        spawn_in_glass(field, building, cell)
    field.tick(building, felix, level=2)
    assert sum(cell.is_broken for cell in cells) == BRICK_WINDOW_BREAKS_PER_SECTION
    field.reset_break_budget()
    field.clear()
    remaining = [cell for cell in cells if not cell.is_broken]
    spawn_in_glass(field, building, remaining[0])
    field.tick(building, felix, level=2)
    assert remaining[0].is_broken


def test_only_intact_windows_can_be_broken_by_bricks():
    building, felix = make_world(level=2)
    field = BrickField(AlwaysNinetyNineRandom())
    cell = upper_window_cells(building)[0]
    building.damage(cell, is_heavy=True)
    spawn_in_glass(field, building, cell)
    field.tick(building, felix, level=2)
    assert field.live_count == 1  # brick passed through, not consumed


def test_ground_bounce_then_disappears():
    building, felix = make_world()
    field = BrickField(random.Random(0))
    field.spawn(10, GROUND_Y - 1)
    field.tick(building, felix, level=1)
    brick = field._bricks[0]
    assert brick.is_bouncing
    for _ in range(BRICK_BOUNCE_TICKS):
        assert field.live_count == 1
        field.tick(building, felix, level=1)
    assert field.live_count == 0


def test_spawn_ignored_past_live_limit():
    field = BrickField(random.Random(0))
    for _ in range(BRICK_MAX_LIVE + 5):
        field.spawn(0, 0)
    assert field.live_count == BRICK_MAX_LIVE


def standing_hitbox(center_x, feet_y):
    return pygame.Rect(center_x - HITBOX_WIDTH // 2, feet_y - HITBOX_HEIGHT,
                       HITBOX_WIDTH, HITBOX_HEIGHT)


def test_falling_brick_above_the_feet_threatens_the_spot():
    field = BrickField(random.Random(0))
    field.spawn(100, 50)
    assert field.is_falling_toward(standing_hitbox(100, 200))
    assert field.is_falling_toward(standing_hitbox(110, 200))  # partial horizontal overlap


def test_brick_past_the_feet_or_beside_the_spot_is_no_threat():
    field = BrickField(random.Random(0))
    field.spawn(100, 210)
    assert not field.is_falling_toward(standing_hitbox(100, 200))
    field.spawn(100, 50)
    edges_just_touch_x = 100 + BRICK_WIDTH // 2 + HITBOX_WIDTH // 2
    assert not field.is_falling_toward(standing_hitbox(edges_just_touch_x, 200))


def test_bouncing_brick_is_no_threat():
    building, felix = make_world()
    field = BrickField(random.Random(0))
    field.spawn(200, GROUND_Y - 1)
    field.tick(building, felix, level=1)
    assert not field.is_falling_toward(standing_hitbox(200, GROUND_Y + 8))


class RecordingSound:
    def __init__(self):
        self.played = []

    def play_sfx(self, name):
        self.played.append(name)


def test_brick_crack_plays_window_break():
    building, felix = make_world(level=2)
    field = BrickField(AlwaysNinetyNineRandom())
    cell = upper_window_cells(building)[0]
    sound = RecordingSound()
    spawn_in_glass(field, building, cell)
    field.tick(building, felix, level=2, sound=sound)
    assert cell.is_broken
    assert sound.played == ["window_break"]


def test_brick_hit_plays_sound_0_and_bounce_plays_sound_3():
    # FUN_0040d490: sound 0 when it hits Felix, sound 3 when it bounces off an invulnerable one.
    building, felix = make_world()
    field = BrickField(random.Random(0))
    sound = RecordingSound()
    spawn_on_felix(field, felix)
    field.tick(building, felix, level=1, sound=sound)
    assert sound.played == ["felix_hit"]

    building, felix = make_world()
    felix.activate_invulnerability()
    sound = RecordingSound()
    spawn_on_felix(field, felix)
    field.tick(building, felix, level=1, sound=sound)
    assert sound.played == ["brick_bounce"]
