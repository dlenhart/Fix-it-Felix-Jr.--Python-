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
    BIRD_SPEED, BIRD_WRAP_LEFT_X, BIRD_WRAP_RIGHT_X, DROP_HAZARD_BLINK_TICKS,
    DROP_HAZARD_MAX_LIVE, Bird, HazardField,
    clear_sill_obstacles, place_sill_obstacles, sill_obstacle_rect,
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


class StubFelix:
    """A Felix standing in a given box; every touch lands a hit unless refused."""

    def __init__(self, hitbox, is_hit_refused=False):
        self.box = hitbox
        self.is_hit_refused = is_hit_refused
        self.hit_count = 0

    def hitbox(self):
        return self.box

    def hit(self, sound=None):
        if self.is_hit_refused:
            return False
        self.hit_count += 1
        return True


def felix_box_on(hazard):
    """A Felix-sized box (12x28, feet at the bottom) centered on the hazard's node."""
    return pygame.Rect(round(hazard.x) - 6, round(hazard.y) - 14, 12, 28)


def drop_one(level=5, ralph_x=72.0, seed=1):
    building = Building(level, random.Random(seed))
    field = HazardField(random.Random(seed))
    field.request_drop(StubRalph(x=ralph_x, y=40.0), building, get_level_config(level))
    return building, field, field.drop_hazards[0]


def test_drop_hazard_gap_follows_ralphs_side():
    for seed in range(100):
        assert drop_one(ralph_x=72.0, seed=seed)[2].gap_index in (0, 1)
        assert drop_one(ralph_x=169.0, seed=seed)[2].gap_index in (2, 3)
        assert drop_one(ralph_x=120.0, seed=seed)[2].gap_index in (1, 2)


def test_drop_hazard_lands_in_the_middle_of_its_gap_at_the_exe_sill_row():
    for seed in range(50):
        building, field, hazard = drop_one(ralph_x=169.0, seed=seed)
        left_cell = hazard.floor.cells[hazard.gap_index]
        right_cell = hazard.floor.cells[hazard.gap_index + 1]
        assert left_cell.x + 23 < hazard.x < right_cell.x
        assert hazard.landing_y == building.sill_y(left_cell)
    gap_zero_hazards = [hazard for seed in range(20)
                        for hazard in [drop_one(ralph_x=72.0, seed=seed)[2]]
                        if hazard.gap_index == 0]
    assert gap_zero_hazards
    assert all(hazard.x == 67 for hazard in gap_zero_hazards)  # (72 - 63) // 2 + 63


def test_door_side_gaps_skip_the_bottom_two_floors_of_the_first_section():
    for seed in range(100):
        building, _, hazard = drop_one(ralph_x=120.0, seed=seed)
        assert hazard.floor in building.section_floors()[2:]


class ScriptedFloorRandom(random.Random):
    """Always picks gap 0 or 2 (randrange 0) and the scripted floor indices, counting the picks."""

    def __new__(cls, floor_picks):
        # random.Random.__new__ would take floor_picks as its seed.
        return super().__new__(cls)

    def __init__(self, floor_picks):
        super().__init__(0)
        self._floor_picks = list(floor_picks)
        self.floor_pick_count = 0

    def randrange(self, *args, **kwargs):
        return 0

    def choice(self, sequence):
        self.floor_pick_count += 1
        return sequence[self._floor_picks.pop(0)]


def test_drop_hazard_rerolls_a_floor_whose_gap_is_taken():
    building = Building(10, random.Random(3))
    rng = ScriptedFloorRandom([1, 1, 3])
    field = HazardField(rng)
    config = get_level_config(10)
    floors = building.section_floors()
    field.request_drop(StubRalph(x=72.0), building, config)
    field.request_drop(StubRalph(x=72.0), building, config)
    assert rng.floor_pick_count == 3  # the second drop picked floor 1, found it taken, rerolled
    assert [(hazard.floor, hazard.gap_index) for hazard in field.drop_hazards] == [
        (floors[1], 0), (floors[3], 0)]


def test_drop_hazard_gives_up_after_four_taken_floors():
    building = Building(10, random.Random(3))
    rng = ScriptedFloorRandom([1, 1, 1, 1, 1])
    field = HazardField(rng)
    config = get_level_config(10)
    field.request_drop(StubRalph(x=72.0), building, config)
    field.request_drop(StubRalph(x=72.0), building, config)
    assert rng.floor_pick_count == 5
    assert len(field.drop_hazards) == 1


def test_falling_drop_hazard_passing_through_felix_does_not_hit():
    building, field, hazard = drop_one()
    felix = StubFelix(felix_box_on(hazard))
    for _ in range(200):
        felix.box = felix_box_on(hazard)
        was_hit = field.tick(building, felix)
        if hazard.is_landed:
            break
        assert was_hit is False
    assert hazard.is_landed
    assert felix.hit_count == (1 if was_hit else 0)  # only the landing tick may hit


def test_landed_drop_hazard_hits_felix_once_then_blinks_away():
    building, field, hazard = drop_one()
    away = StubFelix(pygame.Rect(0, 0, 1, 1))
    for _ in range(200):
        field.tick(building, away)
    assert hazard.is_landed and hazard.y == hazard.landing_y and not hazard.is_blinking

    felix = StubFelix(felix_box_on(hazard))
    assert field.tick(building, felix) is True
    assert hazard.is_blinking and felix.hit_count == 1
    assert DROP_HAZARD_BLINK_TICKS == 105  # FUN_004073f0: 7 phases of 15 ticks
    for _ in range(DROP_HAZARD_BLINK_TICKS - 1):
        assert field.tick(building, felix) is False
    assert field.drop_hazards == (hazard,)
    assert field.tick(building, felix) is False
    assert felix.hit_count == 1
    assert field.drop_hazards == ()


def test_landed_drop_hazard_reaches_a_felix_standing_on_that_floor():
    building, field, hazard = drop_one()
    for _ in range(200):
        field.tick(building, StubFelix(pygame.Rect(0, 0, 1, 1)))
    felix = Felix()
    felix.place_at(building.section_floors().index(hazard.floor), hazard.gap_index, building)
    standing_box = felix.hitbox()
    walking_past = standing_box.move(round(hazard.x) - standing_box.centerx, 0)
    assert hazard.rect().colliderect(walking_past)
    assert not hazard.rect().colliderect(standing_box)  # a window spot stays safe


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

    building, field, hazard = drop_one()
    for _ in range(200):
        field.tick(building, StubFelix(pygame.Rect(0, 0, 1, 1)))
    refusing_felix = StubFelix(felix_box_on(hazard), is_hit_refused=True)
    for _ in range(40):
        assert field.tick(building, refusing_felix) is False
    assert not hazard.is_blinking


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


def test_drop_hazard_threatens_its_gap_while_falling_and_after_landing():
    building, field, hazard = drop_one()
    landing_box = pygame.Rect(round(hazard.x) - 6, round(hazard.landing_y) - 14, 12, 28)
    assert not hazard.is_landed
    assert field.is_threatening(landing_box)
    for _ in range(200):
        field.tick(building, StubFelix(pygame.Rect(0, 0, 1, 1)))
    assert hazard.is_landed
    assert field.is_threatening(landing_box)
    assert not field.is_threatening(landing_box.move(-20, 0))


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


def test_sill_obstacle_rect_rests_on_top_of_the_ledge():
    building = Building(6, random.Random(0))
    for floor in building.section_floors():
        for cell in floor.cells:
            if cell.kind == CellKind.ARCHED:
                continue
            rect = sill_obstacle_rect(building, cell)
            left, right = building.sill_span_x(cell)
            # Exe x (FUN_00406e00: middle of the bounds); [USER] node on the sill;
            # anim 91 origin (11, 5).
            assert rect.topleft == ((right - left) // 2 + left - 11, building.sill_y(cell) - 5)
            assert rect.size == (32, 8)
    plain = building.section_floors()[1].cells[0]
    piece_top = building.section_floors()[1].bottom_y - 48
    rect = sill_obstacle_rect(building, plain)
    assert rect.topleft == (plain.x, piece_top + 31)  # slab art on piece rows 31-36, above the ledge


def test_sill_obstacle_rect_follows_the_bounce():
    building = Building(6, random.Random(0))
    cell = building.section_floors()[2].cells[1]
    cell.has_sill_obstacle = True
    resting_y = sill_obstacle_rect(building, cell).y
    cell.bump_sill_obstacle()
    field = HazardField(random.Random(0))
    bystander = StubFelix(pygame.Rect(0, 0, 1, 1))
    lifts = []
    for _ in range(13):
        field.tick(building, bystander)
        lifts.append(sill_obstacle_rect(building, cell).y - resting_y)
    assert lifts == [-4] * 4 + [-2] * 4 + [-1] * 4 + [0]


class SoundRecorder:
    def __init__(self):
        self.played = []

    def play_sfx(self, name):
        self.played.append(name)


def test_bird_hit_plays_sound_0():
    building, felix, field = bird_field_overlapping_felix()
    sound = SoundRecorder()
    assert field.tick(building, felix, sound) is True
    assert sound.played == ["felix_hit"]  # FUN_00406bb0


def test_drop_hazard_hit_is_silent():
    building, field, hazard = drop_one()
    away = StubFelix(pygame.Rect(0, 0, 1, 1))
    for _ in range(200):
        field.tick(building, away)
    sound = SoundRecorder()
    assert field.tick(building, StubFelix(felix_box_on(hazard)), sound) is True
    assert sound.played == []  # FUN_004073f0 plays nothing
