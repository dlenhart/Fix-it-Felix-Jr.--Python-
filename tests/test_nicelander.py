import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from entities.building import PANE_SMASHED, Building, CellKind  # noqa: E402
from entities.felix import Felix  # noqa: E402
from entities.nicelander import (  # noqa: E402
    FRAME_START_TICKS, NICELANDER_MAX_CANDIDATES, NICELANDER_REARM_TICKS,
    NICELANDER_SPAWN_TICKS, NicelanderDirector,
)
from entities.ralph import RalphState  # noqa: E402
from scenes.game_phases import PlayPhase, SectionClearPhase  # noqa: E402
from sprite_data import NICELANDER_HANDOFF_FRAME_INDEX  # noqa: E402
from test_game_flow import MockInput, make_game, reach_play  # noqa: E402

HANDOFF_TICK = FRAME_START_TICKS[NICELANDER_HANDOFF_FRAME_INDEX]


def smash_bottom_panes(building, local_rows):
    for local_row in local_rows:
        for cell in building.section_floors()[local_row].cells:
            if cell.kind in (CellKind.DOOR, CellKind.ARCHED):
                continue
            cell.bottom_pane = PANE_SMASHED


def make_world(seed=1):
    building = Building(1, random.Random(seed))
    felix = Felix()
    felix.place_at(0, 2, building)
    return building, felix, NicelanderDirector(random.Random(seed))


def spawn_nicelander(building, felix, director):
    smash_bottom_panes(building, (1, 2))
    director.tick(building, felix)
    assert director.nicelander is not None
    return director.nicelander


def tick_to_handoff(building, felix, director):
    for _ in range(HANDOFF_TICK):
        director.tick(building, felix)
    assert director.nicelander.pie is not None


def test_no_nicelander_with_fewer_than_five_broken():
    building, felix, director = make_world()
    for cell in building.section_floors()[2].cells[:4]:
        cell.bottom_pane = PANE_SMASHED
    assert building.broken_count == 4
    for _ in range(NICELANDER_REARM_TICKS * 3):
        director.tick(building, felix)
        assert director.nicelander is None


def test_nicelander_only_in_smashed_bottom_pane_off_felix_floor():
    for seed in range(40):
        building, felix, director = make_world(seed)
        smash_bottom_panes(building, (0, 1, 2))
        # A smashed top pane alone, and a smashed door, are not candidates.
        for cell in building.section_floors()[3].cells:
            cell.top_pane = PANE_SMASHED
        building.section_floors()[0].cells[2].door_damage = PANE_SMASHED
        director.tick(building, felix)
        cell = director.nicelander.cell
        assert cell.bottom_pane == PANE_SMASHED
        assert cell.kind not in (CellKind.DOOR, CellKind.ARCHED)
        assert cell.floor_index != building.section_floors()[felix.local_row].index
        assert cell.floor_index in (1, 2)


def test_spawn_chooses_only_among_first_candidates():
    chosen_columns = set()
    for seed in range(60):
        building, felix, director = make_world(seed)
        smash_bottom_panes(building, (1, 2))
        director.tick(building, felix)
        chosen = director.nicelander.cell
        assert chosen.floor_index == 1  # the first three candidates are all on floor 1
        chosen_columns.add(chosen.column)
    assert len(chosen_columns) == NICELANDER_MAX_CANDIDATES


def test_pie_appears_at_handoff_and_collect_grants_480_and_rage():
    building, felix, director = make_world()
    nicelander = spawn_nicelander(building, felix, director)
    for _ in range(HANDOFF_TICK - 1):
        director.tick(building, felix)
        assert nicelander.pie is None
    director.tick(building, felix)
    assert nicelander.pie is not None

    felix.place_at(nicelander.cell.floor_index, nicelander.cell.column, building)
    assert not felix.is_invulnerable
    assert director.tick(building, felix) is True
    assert felix.is_invulnerable
    assert director.nicelander is None


def test_pie_not_collected_by_felix_elsewhere():
    building, felix, director = make_world()
    spawn_nicelander(building, felix, director)
    tick_to_handoff(building, felix, director)
    assert director.tick(building, felix) is False
    assert not felix.is_invulnerable


def test_fixing_the_window_removes_nicelander_and_pie():
    building, felix, director = make_world()
    nicelander = spawn_nicelander(building, felix, director)
    tick_to_handoff(building, felix, director)
    director.on_window_fixed(nicelander.cell)
    assert director.nicelander is None

    # A fix elsewhere leaves a Nicelander alone.
    other = Building(1, random.Random(2))
    building, felix, director = make_world(2)
    nicelander = spawn_nicelander(building, felix, director)
    director.on_window_fixed(other.section_floors()[0].cells[0])
    assert director.nicelander is nicelander


def test_section_clear_removes_nicelander_and_pie():
    building, felix, director = make_world()
    spawn_nicelander(building, felix, director)
    tick_to_handoff(building, felix, director)
    director.clear()
    assert director.nicelander is None


def test_timer_rearms_to_600_when_too_few_broken():
    building, felix, director = make_world()
    director.tick(building, felix)  # first attempt, nothing broken: 600
    smash_bottom_panes(building, (1, 2))
    for _ in range(NICELANDER_REARM_TICKS):
        director.tick(building, felix)
        assert director.nicelander is None
    director.tick(building, felix)  # timer is 0: the next attempt succeeds
    assert director.nicelander is not None


def test_timer_is_1500_after_a_spawn_and_waits_for_the_nicelander():
    building, felix, director = make_world()
    nicelander = spawn_nicelander(building, felix, director)
    tick_to_handoff(building, felix, director)
    director.on_window_fixed(nicelander.cell)
    # The timer did not count down while the Nicelander was out.
    for _ in range(NICELANDER_SPAWN_TICKS):
        director.tick(building, felix)
        assert director.nicelander is None
    director.tick(building, felix)
    assert director.nicelander is not None


def test_draw_renders_nicelander_and_pie():
    from camera import Camera
    from sprite_sheet import SpriteSheet
    building, felix, director = make_world()
    spawn_nicelander(building, felix, director)
    screen = pygame.Surface((240, 320))
    sprites = SpriteSheet()
    director.draw(screen, sprites, building, Camera(), 0)
    tick_to_handoff(building, felix, director)
    director.draw(screen, sprites, building, Camera(), 0)


def test_collecting_the_pie_in_play_makes_felix_invulnerable_and_ralph_rage():
    _, game = make_game()
    reach_play(game)
    smash_bottom_panes(game.building, (1, 2))
    for _ in range(HANDOFF_TICK + 5):
        game.tick(MockInput())
        if game.nicelanders.nicelander and game.nicelanders.nicelander.pie:
            break
    nicelander = game.nicelanders.nicelander
    assert nicelander is not None and nicelander.pie is not None
    assert isinstance(game.phase, PlayPhase)

    game.felix.place_at(nicelander.cell.floor_index, nicelander.cell.column, game.building)
    game.tick(MockInput())
    assert game.felix.is_invulnerable
    assert game.ralph.state == RalphState.RAGE
    assert game.nicelanders.nicelander is None


def test_section_clear_phase_removes_nicelander():
    _, game = make_game()
    reach_play(game)
    smash_bottom_panes(game.building, (1, 2))
    for _ in range(5):
        game.tick(MockInput())
    assert game.nicelanders.nicelander is not None
    for floor in game.building.section_floors():
        for cell in floor.cells:
            game.building.fix(cell)
    game.tick(MockInput())
    assert isinstance(game.phase, SectionClearPhase)
    game.tick(MockInput())
    assert game.nicelanders.nicelander is None
