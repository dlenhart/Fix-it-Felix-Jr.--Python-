import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from constants import GAME_HEIGHT, GAME_WIDTH  # noqa: E402
from input_handler import Action  # noqa: E402
from scene_manager import SceneManager  # noqa: E402
from scenes.game_over_scene import GameOverScene  # noqa: E402
from entities.felix import FelixState  # noqa: E402
from entities.ralph import RalphState  # noqa: E402
from scenes.game_phases import (  # noqa: E402
    READY_PAUSE_TICKS, SECTION_SCROLL_SPEED,
    LevelEndPhase, LevelStartPhase, PlayPhase, SectionClearPhase,
)
from scenes.game_scene import GameScene, start_level_from_environment  # noqa: E402
from scenes.roof_phases import GameEndPhase, RoofPhase  # noqa: E402

TICK_LIMIT = 5000


class MockInput:
    def __init__(self, just=(), has_lost_focus=False):
        self._just = set(just)
        self._has_lost_focus = has_lost_focus

    def is_just_pressed(self, action):
        return action in self._just

    def is_pressed(self, action):
        return False

    def has_lost_focus(self):
        return self._has_lost_focus


def make_game(seed=1):
    manager = SceneManager()
    game = GameScene(manager, rng=random.Random(seed))
    manager.push(game)
    return manager, game


def tick_until(game, condition):
    for _ in range(TICK_LIMIT):
        if condition():
            return
        game.tick(MockInput())
    raise AssertionError("condition never became true")


def fix_section(game):
    for floor in game.building.section_floors():
        for cell in floor.cells:
            game.building.fix(cell)


def reach_play(game):
    tick_until(game, lambda: isinstance(game.phase, PlayPhase))


def spawn_brick_on_felix(game):
    hitbox = game.felix.hitbox()
    game.bricks.spawn(hitbox.centerx, hitbox.bottom - 4)


def test_level_start_damages_section_zero_then_plays():
    _, game = make_game()
    assert isinstance(game.phase, LevelStartPhase)
    reach_play(game)
    assert game.building.broken_count > 0
    door = game.building.cell(0, 2)
    assert door.is_broken


def test_level_start_shows_ready_pause_after_climb():
    _, game = make_game()
    tick_until(game, lambda: game.phase.is_ready_countdown)
    ready_ticks = 0
    while isinstance(game.phase, LevelStartPhase):
        game.tick(MockInput())
        ready_ticks += 1
    assert ready_ticks == 180


def test_ralph_idles_through_ready_countdown_then_patrols():
    _, game = make_game()
    tick_until(game, lambda: game.phase.is_ready_countdown)
    ralph = game.ralph
    before = (ralph.x, ralph.y, ralph.state)
    assert ralph.state == RalphState.IDLE
    for _ in range(READY_PAUSE_TICKS - 1):
        game.tick(MockInput())
        assert (ralph.x, ralph.y, ralph.state) == before
    assert isinstance(game.phase, LevelStartPhase)

    game.tick(MockInput())
    assert isinstance(game.phase, PlayPhase)
    assert ralph.state == RalphState.WALK
    assert (ralph.x, ralph.y) == (120, game.building.ledge_y())


def test_fixing_all_windows_clears_section_scrolls_and_resumes():
    _, game = make_game()
    reach_play(game)
    fix_section(game)
    game.tick(MockInput())
    assert isinstance(game.phase, SectionClearPhase)
    reach_play(game)
    assert game.building.section_index == 1
    assert game.camera.scroll_y == game.building.scroll_target(1)
    assert game.felix.local_row == 0
    assert game.building.broken_count > 0


class RecordingSound:
    """Stands in for SoundManager and logs every call in order."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, *args, *kwargs.values()))
        return record

    def music(self):
        return [call[1:] for call in self.calls if call[0] == "play_music_index"]


def test_gameplay_music_is_exe_sound_14_and_starts_with_play():
    _, game = make_game()
    game.sound = RecordingSound()
    tick_until(game, lambda: isinstance(game.phase, LevelStartPhase) and game.phase.is_ready_countdown)
    assert game.sound.music() == []  # nothing starts it during the climb-in or ready pause
    reach_play(game)
    assert game.sound.music() == [(0xE, True)]


def test_section_clear_jingle_replaces_the_music_until_play_resumes():
    _, game = make_game()
    game.sound = RecordingSound()
    reach_play(game)
    fix_section(game)
    game.tick(MockInput())
    assert isinstance(game.phase, SectionClearPhase)
    assert game.sound.music() == [(0xE, True), (0x16, False)]  # on the fixing tick
    # FUN_00409ac0 stops the pie's invulnerability tune on every clear, before the jingle.
    jingle_call = game.sound.calls.index(("play_music_index", 0x16, False))
    assert ("stop_sound_index", 0x19) in game.sound.calls[:jingle_call]
    reach_play(game)
    assert game.sound.music() == [(0xE, True), (0x16, False), (0xE, True)]


def test_final_hit_plays_sound_21_as_music_and_game_over_is_silent():
    manager, game = make_game()
    game.sound = RecordingSound()
    reach_play(game)
    game.felix.lives = 1
    spawn_brick_on_felix(game)
    game.tick(MockInput())
    assert game.sound.music()[-1] == (0x15, False)  # FUN_0040ca00 replaces sound 14
    calls_at_hit = len(game.sound.calls)
    tick_until(game, lambda: manager.current is not game)
    assert isinstance(manager.current, GameOverScene)
    assert game.sound.calls[calls_at_hit:] == []  # exe states 7/8 never touch the music


def test_section_transition_follows_the_exe_state_5_schedule():
    _, game = make_game()
    game.sound = RecordingSound()
    reach_play(game)
    fix_section(game)
    game.tick(MockInput())  # the fixing tick clears the section
    assert isinstance(game.phase, SectionClearPhase)
    assert game.ralph.state == RalphState.SECTION_POSE
    ledge_before = game.ralph.y
    for _ in range(0x78 - 1):
        game.tick(MockInput())
        assert game.ralph.state == RalphState.SECTION_POSE
    game.tick(MockInput())  # the climb timer runs out: anim 27, no move yet
    assert game.ralph.state == RalphState.CLIMB and game.ralph.y == ledge_before
    tick_until(game, lambda: game.ralph.state == RalphState.IDLE)
    assert ("play_sound_index", 0x1D) in game.sound.calls  # FUN_00408810, at the ledge
    reach_play(game)


def test_entering_a_new_section_ends_invulnerability():
    _, game = make_game()
    reach_play(game)
    game.felix.activate_invulnerability()
    fix_section(game)
    game.tick(MockInput())
    assert isinstance(game.phase, SectionClearPhase)
    reach_play(game)
    assert not game.felix.is_invulnerable  # FUN_0040cac0


def test_last_section_goes_to_level_end_then_next_level_keeps_lives_and_score():
    _, game = make_game()
    reach_play(game)
    game.felix.score = 1234
    game.felix.lives = 7
    for _ in range(game.building.section_count):
        fix_section(game)
        tick_until(game, lambda: not isinstance(game.phase, PlayPhase))
        tick_until(game, lambda: isinstance(game.phase, (PlayPhase, LevelEndPhase)))
    assert isinstance(game.phase, LevelEndPhase)

    tick_until(game, lambda: game.level == 2)
    assert isinstance(game.phase, LevelStartPhase)
    assert game.building.section_index == 0
    assert game.camera.scroll_y == 0
    assert (game.felix.score, game.felix.lives) == (1234, 7)


def test_last_section_skips_the_section_clear_and_waits_for_the_roof():
    _, game = make_game()
    reach_play(game)
    for _ in range(game.building.section_count - 1):
        fix_section(game)
        tick_until(game, lambda: not isinstance(game.phase, PlayPhase))
        tick_until(game, lambda: isinstance(game.phase, PlayPhase))
    fix_section(game)
    game.tick(MockInput())
    assert isinstance(game.phase, LevelEndPhase)
    tick_until(game, lambda: isinstance(game.phase, RoofPhase))
    assert game.level == 1


def hammer_for(game, tick_count):
    for _ in range(tick_count):
        game.tick(MockInput([Action.JUMP]))


def test_no_hits_or_scoring_during_level_start():
    _, game = make_game()
    game.tick(MockInput())
    door = game.building.cell(0, 2)
    assert (game.felix.local_row, game.felix.column) == (0, 2)
    assert door.is_broken
    lives_before, score_before = game.felix.lives, game.felix.score
    spawn_brick_on_felix(game)
    hammer_for(game, 60)
    assert isinstance(game.phase, LevelStartPhase)
    assert door.is_broken
    assert (game.felix.lives, game.felix.score) == (lives_before, score_before)


def test_no_hits_or_scoring_outside_play_phase():
    _, game = make_game()
    reach_play(game)
    fix_section(game)
    game.tick(MockInput())
    assert isinstance(game.phase, SectionClearPhase)
    lives_before, score_before = game.felix.lives, game.felix.score
    spawn_brick_on_felix(game)
    hammer_for(game, 30)
    assert isinstance(game.phase, SectionClearPhase)
    assert (game.felix.lives, game.felix.score) == (lives_before, score_before)


def test_game_over_fires_once():
    manager, game = make_game()
    reach_play(game)
    game.felix.lives = 1
    replace_calls = []
    original_replace = manager.replace

    def counting_replace(scene):
        replace_calls.append(scene)
        original_replace(scene)

    manager.replace = counting_replace
    spawn_brick_on_felix(game)
    game.tick(MockInput())
    assert game.felix.state == FelixState.FINAL_HIT_ANIM
    assert manager.current is game  # Ruling 13: not on the fatal hit

    tick_until(game, lambda: manager.current is not game)
    assert game.felix.state == FelixState.GAME_OVER
    assert game.felix.lives == 0
    assert len(replace_calls) == 1
    assert isinstance(manager.current, GameOverScene)

    game.end_game()
    game.tick(MockInput())
    assert len(replace_calls) == 1


def frozen_world(game):
    return ((game.ralph.x, game.ralph.y, game.ralph.state),
            [(brick.x, brick.y) for brick in game.bricks._bricks])


def test_hit_freezes_ralph_and_bricks_until_respawn():
    _, game = make_game()
    reach_play(game)
    tick_until(game, lambda: game.bricks.live_count >= 2)
    spawn_brick_on_felix(game)
    game.tick(MockInput())
    assert game.felix.state == FelixState.HIT_ANIM
    lives_before = game.felix.lives
    before = frozen_world(game)
    assert before[1]  # other bricks are still in flight
    while game.felix.is_in_hit_sequence:
        game.tick(MockInput())
        if game.felix.is_in_hit_sequence:
            assert frozen_world(game) == before
    assert isinstance(game.phase, PlayPhase)
    assert game.felix.lives == lives_before - 1
    game.tick(MockInput())
    assert frozen_world(game) != before


def test_respawn_restarts_ralphs_patrol():
    _, game = make_game()
    reach_play(game)
    tick_until(game, lambda: game.ralph.state == RalphState.POUND)
    spawn_brick_on_felix(game)
    game.tick(MockInput())
    assert game.felix.is_in_hit_sequence
    tick_until(game, lambda: not game.felix.is_in_hit_sequence)
    assert game.ralph.state == RalphState.WALK  # FUN_0040e220 -> FUN_0040df60(0)


def test_ralph_animates_through_the_ready_countdown():
    _, game = make_game()
    tick_until(game, lambda: isinstance(game.phase, LevelStartPhase) and game.phase.is_ready_countdown)
    shown = set()
    for _ in range(30):
        game.tick(MockInput())
        shown.add(game.ralph.frame_id)
    assert shown == {80, 81}  # anim 26, as FUN_0040dbb0 leaves him on the ledge


def test_respawn_avoids_a_frozen_brick_above_the_hit_cell():
    _, game = make_game()
    reach_play(game)
    game.bricks.clear()
    hit_column = game.felix.column
    spawn_brick_on_felix(game)
    game.tick(MockInput())
    assert game.felix.is_in_hit_sequence
    hitbox = game.felix.hitbox()
    game.bricks.spawn(hitbox.centerx, hitbox.top - 4)  # frozen right above his head

    tick_until(game, lambda: not game.felix.is_in_hit_sequence)
    assert game.felix.column != hit_column
    assert not game.bricks.is_falling_toward(game.felix.hitbox())


def hit_felix_and_freeze_bricks_above(game, columns, height_above_head):
    """Hit Felix with a brick, then hang frozen bricks over the given columns of his floor."""
    game.bricks.clear()
    spawn_brick_on_felix(game)
    game.tick(MockInput())
    assert game.felix.is_in_hit_sequence
    head_y = game.felix.hitbox().top
    for column in columns:
        cell = game.building.cell(game.felix.local_row, column)
        game.bricks.spawn(cell.center_x, head_y - height_above_head)


def test_respawn_avoids_a_brick_still_falling_from_floors_above():
    _, game = make_game()
    reach_play(game)
    hit_column = game.felix.column
    lives_before = game.felix.lives
    hit_felix_and_freeze_bricks_above(game, [hit_column], height_above_head=150)

    tick_until(game, lambda: not game.felix.is_in_hit_sequence)
    assert game.felix.column != hit_column
    assert game.felix.lives == lives_before - 1
    assert not game.bricks.is_falling_toward(game.felix.hitbox())


def test_respawn_skips_a_threatened_neighbour_for_the_next_safe_column():
    _, game = make_game()
    reach_play(game)
    assert game.felix.column == 2
    # Neighbours 1 and 3 tie on distance and on distance to the center; 1 comes first.
    hit_felix_and_freeze_bricks_above(game, [2, 1], height_above_head=4)

    tick_until(game, lambda: not game.felix.is_in_hit_sequence)
    assert game.felix.column == 3
    assert not game.bricks.is_falling_toward(game.felix.hitbox())


def test_final_hit_freezes_ralph_and_bricks():
    _, game = make_game()
    reach_play(game)
    game.felix.lives = 1
    tick_until(game, lambda: game.bricks.live_count >= 2)
    spawn_brick_on_felix(game)
    game.tick(MockInput())
    before = frozen_world(game)
    for _ in range(100):
        game.tick(MockInput())
        assert frozen_world(game) == before


def test_draw_renders_hit_sequence():
    _, game = make_game()
    surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
    reach_play(game)
    for lives in (5, 1):
        game.felix.lives = lives
        spawn_brick_on_felix(game)
        game.tick(MockInput())
        assert game.felix.is_in_hit_sequence
        for _ in range(400):
            if not game.felix.is_in_hit_sequence or game.felix.is_game_over:
                break
            game.draw(surface, alpha=0.5)
            game.tick(MockInput())


def test_pause_freezes_scroll_and_climb():
    _, game = make_game()
    reach_play(game)
    fix_section(game)
    tick_until(game, lambda: isinstance(game.phase, SectionClearPhase) and game.phase.is_climbing)
    for _ in range(5):
        game.tick(MockInput())

    def frozen_state():
        phase = game.phase
        return (game.camera.scroll_y, game.ralph.x, game.ralph.y,
                phase.pose_ticks, phase.is_climbing, phase.is_scrolling)

    game.tick(MockInput([Action.PAUSE]))
    before = frozen_state()
    for _ in range(300):
        game.tick(MockInput())
    assert frozen_state() == before

    ralph_before = (game.ralph.x, game.ralph.y)
    game.tick(MockInput([Action.PAUSE]))  # the unpausing tick also runs the phase
    ralph_moved = abs(game.ralph.x - ralph_before[0]) + abs(game.ralph.y - ralph_before[1])
    assert ralph_moved == 1
    tick_until(game, lambda: game.phase.is_scrolling)
    game.tick(MockInput([Action.PAUSE]))
    scroll_before = game.camera.scroll_y
    for _ in range(30):
        game.tick(MockInput())
    assert game.camera.scroll_y == scroll_before

    game.tick(MockInput([Action.PAUSE]))
    target = game.building.scroll_target(game.building.section_index)
    assert game.camera.scroll_y == min(scroll_before + SECTION_SCROLL_SPEED, target)


def test_draw_renders_every_phase():
    _, game = make_game()
    surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
    game.felix.lives = 12
    game.is_end_game_requested = True
    seen_phases = set()
    game.draw(surface, alpha=0.5)
    reach_play(game)
    for _ in range(game.building.section_count):
        fix_section(game)
        for _ in range(TICK_LIMIT):
            game.tick(MockInput())
            game.draw(surface, alpha=0.5)
            seen_phases.add(type(game.phase))
            if isinstance(game.phase, (PlayPhase, GameEndPhase)):
                break
    for _ in range(10):
        game.tick(MockInput())
        game.draw(surface, alpha=0.5)
    assert {SectionClearPhase, PlayPhase, LevelEndPhase, RoofPhase, GameEndPhase} <= seen_phases


def test_start_level_defaults_to_one(monkeypatch):
    monkeypatch.delenv("FELIX_START_LEVEL", raising=False)
    assert start_level_from_environment() == 1


def test_start_level_reads_the_environment(monkeypatch):
    monkeypatch.setenv("FELIX_START_LEVEL", "5")
    assert start_level_from_environment() == 5


@pytest.mark.parametrize("raw_level", ["abc", "0", "-2"])
def test_start_level_rejects_bad_values(monkeypatch, raw_level):
    monkeypatch.setenv("FELIX_START_LEVEL", raw_level)
    with pytest.raises(ValueError):
        start_level_from_environment()
