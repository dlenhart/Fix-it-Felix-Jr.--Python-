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


def run_out_timer(building, felix, director, ticks=NICELANDER_SPAWN_TICKS):
    """Tick through a countdown; no Nicelander appears while it runs."""
    for _ in range(ticks):
        director.tick(building, felix, is_ralph_patrolling=True)
        assert director.nicelander is None


def due_director(building, felix, seed=1):
    """A director whose level-start countdown has run out: the next tick spawns."""
    director = NicelanderDirector(random.Random(seed))
    smash_bottom_panes(building, (1, 2))
    run_out_timer(building, felix, director)
    return director


def spawn_nicelander(building, felix, director):
    smash_bottom_panes(building, (1, 2))
    run_out_timer(building, felix, director)
    director.tick(building, felix, is_ralph_patrolling=True)
    assert director.nicelander is not None
    return director.nicelander


def tick_to_handoff(building, felix, director):
    for _ in range(HANDOFF_TICK):
        director.tick(building, felix, is_ralph_patrolling=True)
    assert director.nicelander.pie is not None


def test_first_spawn_waits_out_the_1500_tick_level_timer():
    building, felix, director = make_world()
    smash_bottom_panes(building, (1, 2))
    run_out_timer(building, felix, director)
    director.tick(building, felix, is_ralph_patrolling=True)
    assert director.nicelander is not None


def test_countdown_ending_with_fewer_than_five_broken_rearms_600():
    building, felix, director = make_world()
    for cell in building.section_floors()[2].cells[:4]:
        cell.bottom_pane = PANE_SMASHED
    assert building.broken_count == 4
    run_out_timer(building, felix, director, NICELANDER_SPAWN_TICKS + NICELANDER_REARM_TICKS * 2)
    # Enough broken windows when the re-armed countdown next runs out.
    smash_bottom_panes(building, (1,))
    run_out_timer(building, felix, director, NICELANDER_REARM_TICKS)
    director.tick(building, felix, is_ralph_patrolling=True)
    assert director.nicelander is not None


def test_at_zero_the_spawn_needs_no_minimum_and_retries_every_tick():
    building, felix, director = make_world()
    smash_bottom_panes(building, (1, 2))
    run_out_timer(building, felix, director)
    for floor in building.section_floors():
        for cell in floor.cells:
            building.fix(cell)
    # FUN_00407190 finds no candidate and returns: the timer stays 0.
    for _ in range(NICELANDER_REARM_TICKS * 2):
        director.tick(building, felix, is_ralph_patrolling=True)
        assert director.nicelander is None
    # One smashed window is enough at 0; the broken minimum is only checked by the countdown.
    building.section_floors()[1].cells[0].bottom_pane = PANE_SMASHED
    assert building.broken_count < 5
    director.tick(building, felix, is_ralph_patrolling=True)
    assert director.nicelander is not None


def test_nicelander_only_in_smashed_bottom_pane_off_felix_floor():
    for seed in range(40):
        building, felix, director = make_world(seed)
        smash_bottom_panes(building, (0, 1, 2))
        # A smashed top pane alone, and a smashed door, are not candidates.
        for cell in building.section_floors()[3].cells:
            cell.top_pane = PANE_SMASHED
        building.section_floors()[0].cells[2].door_damage = PANE_SMASHED
        run_out_timer(building, felix, director)
        director.tick(building, felix, is_ralph_patrolling=True)
        cell = director.nicelander.cell
        assert cell.bottom_pane == PANE_SMASHED
        assert cell.kind not in (CellKind.DOOR, CellKind.ARCHED)
        assert cell.floor_index != building.section_floors()[felix.local_row].index
        assert cell.floor_index in (1, 2)


def test_spawn_chooses_only_among_first_candidates():
    chosen_columns = set()
    for seed in range(60):
        building, felix, director = make_world(seed)
        director = due_director(building, felix, seed)
        director.tick(building, felix, is_ralph_patrolling=True)
        chosen = director.nicelander.cell
        assert chosen.floor_index == 1  # the first three candidates are all on floor 1
        chosen_columns.add(chosen.column)
    assert len(chosen_columns) == NICELANDER_MAX_CANDIDATES


def test_pie_appears_at_handoff_and_collect_grants_480_and_rage():
    building, felix, director = make_world()
    nicelander = spawn_nicelander(building, felix, director)
    for _ in range(HANDOFF_TICK - 1):
        director.tick(building, felix, is_ralph_patrolling=True)
        assert nicelander.pie is None
    director.tick(building, felix, is_ralph_patrolling=True)
    assert nicelander.pie is not None

    felix.place_at(nicelander.cell.floor_index, nicelander.cell.column, building)
    assert not felix.is_invulnerable
    assert director.tick(building, felix, is_ralph_patrolling=True) is True
    assert felix.is_invulnerable
    assert director.nicelander is None


def test_pie_not_collected_by_felix_elsewhere():
    building, felix, director = make_world()
    spawn_nicelander(building, felix, director)
    tick_to_handoff(building, felix, director)
    assert director.tick(building, felix, is_ralph_patrolling=True) is False
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


def test_section_clear_removes_nicelander_and_pie_and_keeps_the_timer():
    building, felix, director = make_world()
    spawn_nicelander(building, felix, director)
    tick_to_handoff(building, felix, director)
    director.clear()
    assert director.nicelander is None
    # FUN_00409ac0 leaves the timer: the 1500 set at the spawn still has to run out.
    run_out_timer(building, felix, director)
    director.tick(building, felix, is_ralph_patrolling=True)
    assert director.nicelander is not None


def test_timer_is_1500_after_a_spawn_and_waits_for_the_nicelander():
    building, felix, director = make_world()
    nicelander = spawn_nicelander(building, felix, director)
    tick_to_handoff(building, felix, director)
    director.on_window_fixed(nicelander.cell)
    # The timer did not count down while the Nicelander was out.
    run_out_timer(building, felix, director)
    director.tick(building, felix, is_ralph_patrolling=True)
    assert director.nicelander is not None


def test_no_spawn_or_countdown_while_ralph_is_not_patrolling():
    building, felix, director = make_world()
    smash_bottom_panes(building, (1, 2))
    # FUN_004084c0 skips the timer and the spawn outside Ralph states 0/1.
    for _ in range(NICELANDER_SPAWN_TICKS * 2):
        director.tick(building, felix, is_ralph_patrolling=False)
        assert director.nicelander is None
    run_out_timer(building, felix, director)
    for _ in range(3):
        director.tick(building, felix, is_ralph_patrolling=False)
        assert director.nicelander is None
    director.tick(building, felix, is_ralph_patrolling=True)
    assert director.nicelander is not None


def test_no_spawn_while_felix_is_in_his_hit_sequence():
    building, felix, director = make_world()
    director = due_director(building, felix)
    assert felix.hit()
    director.tick(building, felix, is_ralph_patrolling=True)
    assert director.nicelander is None


def test_a_nicelander_already_out_keeps_rising_while_ralph_is_not_patrolling():
    building, felix, director = make_world()
    nicelander = spawn_nicelander(building, felix, director)
    for _ in range(HANDOFF_TICK):
        director.tick(building, felix, is_ralph_patrolling=False)
    assert nicelander.pie is not None


def test_play_phase_gates_spawns_on_ralph_patrolling():
    _, game = make_game()
    reach_play(game)
    smash_bottom_panes(game.building, (1, 2))
    game.nicelanders = due_director(game.building, game.felix)
    game.ralph.start_rage()
    game.tick(MockInput())
    assert game.nicelanders.nicelander is None

    game.ralph.restart_patrol()
    game.tick(MockInput())
    assert game.nicelanders.nicelander is not None


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
    game.nicelanders = due_director(game.building, game.felix)
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
    game.nicelanders = due_director(game.building, game.felix)
    game.tick(MockInput())
    assert game.nicelanders.nicelander is not None
    for floor in game.building.section_floors():
        for cell in floor.cells:
            game.building.fix(cell)
    game.tick(MockInput())
    assert isinstance(game.phase, SectionClearPhase)
    game.tick(MockInput())
    assert game.nicelanders.nicelander is None
