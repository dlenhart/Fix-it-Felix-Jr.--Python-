import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from entities.building import Building  # noqa: E402
from entities.felix import Felix  # noqa: E402
from entities.hazards import (  # noqa: E402
    BIRD_SPEED, BIRD_WRAP_LEFT_X, BIRD_WRAP_RIGHT_X, DROP_HAZARD_BLINKS,
    DROP_HAZARD_BLINK_HALF_PERIOD_TICKS, DROP_HAZARD_MAX_LIVE, Bird, HazardField,
    clear_sill_obstacles, place_sill_obstacles,
)
from level_config import CellKind, get_level_config  # noqa: E402
from scenes.game_phases import PlayPhase, SectionClearPhase  # noqa: E402
from test_game_flow import MockInput, fix_section, make_game, reach_play, tick_until  # noqa: E402


class StubRalph:
    def __init__(self, x=120.0, y=100.0):
        self.x = x
        self.y = y


def make_world(level, seed=1):
    building = Building(level, random.Random(seed))
    felix = Felix()
    felix.place_at(0, 2, building)
    return building, felix, HazardField(random.Random(seed))


def section_cells(building):
    return [cell for floor in building.section_floors() for cell in floor.cells]


def test_sill_obstacles_top_three_floors_max_two_per_floor_never_arched():
    for seed in range(200):
        building = Building(6, random.Random(seed))
        place_sill_obstacles(building, 4, random.Random(seed))
        floors = building.section_floors()
        assert not any(cell.has_sill_obstacle for cell in floors[0].cells)
        assert sum(cell.has_sill_obstacle for cell in section_cells(building)) == 4
        for floor in floors[1:]:
            assert sum(cell.has_sill_obstacle for cell in floor.cells) <= 2
            assert not any(cell.has_sill_obstacle and cell.kind == CellKind.ARCHED
                           for cell in floor.cells)


def test_no_hazards_before_their_levels():
    building, felix, field = make_world(2)
    field.start_section(building, get_level_config(2))
    assert not any(cell.has_sill_obstacle for cell in section_cells(building))
    assert field.birds == ()
    field.request_drop(StubRalph(), building, get_level_config(2))
    assert field.drop_hazards == ()

    building, felix, field = make_world(3)
    field.start_section(building, get_level_config(3))
    assert sum(cell.has_sill_obstacle for cell in section_cells(building)) == 2
    assert field.birds == ()
    field.request_drop(StubRalph(), building, get_level_config(3))
    assert field.drop_hazards == ()


def test_bird_moves_half_pixel_and_wraps():
    building, _, _ = make_world(4)
    floor = building.section_floors()[1]
    from_left = Bird(floor, is_from_right=False)
    from_right = Bird(floor, is_from_right=True)
    assert (from_left.x, from_right.x) == (BIRD_WRAP_LEFT_X, BIRD_WRAP_RIGHT_X)
    from_left.tick()
    from_right.tick()
    assert from_left.x == BIRD_WRAP_LEFT_X + BIRD_SPEED
    assert from_right.x == BIRD_WRAP_RIGHT_X - BIRD_SPEED

    ticks_to_cross = int((BIRD_WRAP_RIGHT_X - BIRD_WRAP_LEFT_X) / BIRD_SPEED)
    for _ in range(ticks_to_cross - 1):
        from_left.tick()
        from_right.tick()
    assert from_left.x == BIRD_WRAP_RIGHT_X
    assert from_right.x == BIRD_WRAP_LEFT_X
    from_left.tick()
    from_right.tick()
    assert from_left.x == BIRD_WRAP_LEFT_X
    assert from_right.x == BIRD_WRAP_RIGHT_X


def bird_field_overlapping_felix(level=4):
    """A level-4 world whose first bird sits on Felix's floor and hitbox."""
    building, felix, field = make_world(level)
    field.start_section(building, get_level_config(level))
    bird = field.birds[0]
    bird.floor = building.section_floors()[felix.local_row]
    bird.x = float(felix.hitbox().x)
    return building, felix, field


def test_bird_hits_felix_unless_invulnerable():
    building, felix, field = bird_field_overlapping_felix()
    felix.activate_invulnerability()
    assert field.tick(building, felix) is False
    assert not felix.is_in_hit_sequence

    building, felix, field = bird_field_overlapping_felix()
    assert field.tick(building, felix) is True
    assert felix.is_in_hit_sequence


def force_drop_on_felix_floor(level=5):
    """Retry seeds until the random floor is Felix's, so the hazard lands on his cell."""
    for seed in range(200):
        building, felix, field = make_world(level, seed)
        felix_cell = building.cell(felix.local_row, felix.column)
        ralph = StubRalph(x=felix_cell.center_x, y=building.sill_y(felix_cell) - 20)
        field.request_drop(ralph, building, get_level_config(level))
        if field.drop_hazards[0].target_cell is felix_cell:
            return building, felix, field
    raise AssertionError("no seed targeted Felix's cell")


def test_drop_hazard_lands_on_sill_and_hits_felix_once():
    building, felix, field = force_drop_on_felix_floor()
    hazard = field.drop_hazards[0]
    sill_y = building.sill_y(hazard.target_cell)
    bystander = bystander_felix(building)
    ticks = 0
    while not hazard.is_landed:
        assert field.tick(building, bystander) is False
        ticks += 1
        assert ticks < 200
    assert hazard.y == sill_y
    for _ in range(30):  # it stays put on the sill
        field.tick(building, bystander)
    assert hazard.y == sill_y and not hazard.is_blinking

    assert field.tick(building, felix) is True
    assert hazard.is_blinking
    felix.place_at(felix.local_row, felix.column, building)  # as if respawned on top of it
    blink_ticks = DROP_HAZARD_BLINKS * 2 * DROP_HAZARD_BLINK_HALF_PERIOD_TICKS
    for _ in range(blink_ticks):
        assert field.tick(building, felix) is False
    assert field.drop_hazards == ()


def test_drop_hazards_capped_by_level_and_three():
    building, _, field = make_world(5)
    config = get_level_config(5)
    for _ in range(5):
        field.request_drop(StubRalph(), building, config)
    assert len(field.drop_hazards) == config.drop_hazards == 1

    building, _, field = make_world(10)
    config = get_level_config(10)
    for _ in range(10):
        field.request_drop(StubRalph(), building, config)
    assert len(field.drop_hazards) == DROP_HAZARD_MAX_LIVE


def test_hazard_touch_during_hit_sequence_does_nothing():
    building, felix, field = bird_field_overlapping_felix()
    assert felix.hit()
    assert field.tick(building, felix) is False

    building, felix, field = force_drop_on_felix_floor()
    assert felix.hit()
    for _ in range(40):
        assert field.tick(building, felix) is False
    assert not field.drop_hazards[0].is_blinking


def test_birds_return_to_start_x_at_respawn():
    _, game = make_game()
    game.start_level(4)
    reach_play(game)
    game.hazards.clear()
    game.hazards.start_section(game.building, get_level_config(4))
    for _ in range(30):
        game.tick(MockInput())
    assert all(bird.x != (BIRD_WRAP_RIGHT_X if bird.is_from_right else BIRD_WRAP_LEFT_X)
               for bird in game.hazards.birds)

    assert game.felix.hit()
    tick_until(game, lambda: not game.felix.is_in_hit_sequence)
    for bird in game.hazards.birds:
        start_x = BIRD_WRAP_RIGHT_X if bird.is_from_right else BIRD_WRAP_LEFT_X
        assert abs(bird.x - start_x) <= BIRD_SPEED  # reset, then moved on the respawn tick


def bystander_felix(building):
    """An invulnerable Felix on the top floor, so ticking a field never hits him."""
    felix = Felix()
    felix.place_at(3, 0, building)
    felix.activate_invulnerability()
    return felix


def land_all_drops(building, field):
    bystander = bystander_felix(building)
    for _ in range(200):
        field.tick(building, bystander)


def test_respawn_avoids_a_landed_drop_hazard():
    building, felix, field = force_drop_on_felix_floor()
    land_all_drops(building, field)
    hazard = field.drop_hazards[0]
    assert hazard.is_landed
    assert field.is_threatening(felix.hitbox())

    hit_column = felix.column
    assert felix.hit()
    for _ in range(500):
        felix.tick(MockInput(), building, is_spot_threatened=field.is_threatening)
        if not felix.is_in_hit_sequence:
            break
    assert not felix.is_in_hit_sequence
    assert felix.column != hit_column
    assert not field.is_threatening(felix.hitbox())


def test_respawn_avoids_a_drop_hazard_still_falling_toward_the_spot():
    building, felix, field = force_drop_on_felix_floor()
    assert not field.drop_hazards[0].is_landed
    assert field.is_threatening(felix.hitbox())


def test_section_clear_removes_hazards_and_obstacle_flags_and_next_section_places_more():
    _, game = make_game()
    game.start_level(4)
    reach_play(game)
    assert game.hazards.birds
    old_cells = section_cells(game.building)
    assert any(cell.has_sill_obstacle for cell in old_cells)
    fix_section(game)
    game.tick(MockInput())  # PlayPhase notices the clear
    game.tick(MockInput())  # SectionClearPhase starts
    assert isinstance(game.phase, SectionClearPhase)
    assert game.hazards.birds == ()
    assert not any(cell.has_sill_obstacle for cell in old_cells)
    tick_until(game, lambda: isinstance(game.phase, PlayPhase))
    assert game.hazards.birds
    assert any(cell.has_sill_obstacle for cell in section_cells(game.building))


def test_clear_sill_obstacles_resets_the_active_section():
    building = Building(6, random.Random(1))
    place_sill_obstacles(building, 4, random.Random(1))
    clear_sill_obstacles(building)
    assert not any(cell.has_sill_obstacle for cell in section_cells(building))


def test_draw_renders_every_hazard():
    _, game = make_game()
    game.start_level(5)
    reach_play(game)
    game.hazards.request_drop(game.ralph, game.building, get_level_config(5))
    game.tick(MockInput())
    assert game.hazards.birds and game.hazards.drop_hazards
    game.draw(pygame.Surface((240, 320)))


def test_bird_hit_costs_exactly_one_life():
    _, game = make_game()
    game.start_level(4)
    reach_play(game)
    game.bricks.clear()
    lives_before = game.felix.lives
    bird = game.hazards.birds[0]
    bird.floor = game.building.section_floors()[game.felix.local_row]
    bird.x = float(game.felix.hitbox().x)
    game.tick(MockInput())
    assert game.felix.is_in_hit_sequence
    tick_until(game, lambda: not game.felix.is_in_hit_sequence)
    for _ in range(30):
        game.tick(MockInput())
        game.bricks.clear()
    assert game.felix.lives == lives_before - 1
    assert not game.felix.is_in_hit_sequence
