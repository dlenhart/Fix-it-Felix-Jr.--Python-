import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from constants import GAME_HEIGHT, GAME_WIDTH  # noqa: E402
from input_handler import Action  # noqa: E402
from scene_manager import SceneManager  # noqa: E402
from scenes.game_phases import LevelStartPhase, PlayPhase  # noqa: E402
from scenes.game_scene import GameScene  # noqa: E402


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


def make_game(seed=3):
    manager = SceneManager()
    game = GameScene(manager, rng=random.Random(seed))
    manager.push(game)
    return game


def reach_play(game):
    for _ in range(5000):
        if isinstance(game.phase, PlayPhase):
            return
        game.tick(MockInput())
    raise AssertionError("never reached PlayPhase")


def world_snapshot(game):
    """Everything a paused game must hold still, read through public attributes only."""
    phase = game.phase
    # Only LevelStartPhase has progress fields; read them directly so a rename fails loudly.
    phase_progress = ((phase.has_climb_started, phase.ready_ticks_remaining)
                      if isinstance(phase, LevelStartPhase) else ())
    return (type(phase),
            phase_progress,
            game.camera.scroll_y,
            game.felix.world_pos(), game.felix.state,
            game.ralph.x, game.ralph.y, game.ralph.state,
            [(brick.x, brick.y) for brick in game.bricks.bricks])


def test_pause_key_toggles():
    for pause_action in (Action.START, Action.PAUSE):
        game = make_game()
        game.tick(MockInput([pause_action]))
        assert game.is_paused
        game.tick(MockInput([pause_action]))
        assert not game.is_paused


def test_paused_level_start_does_not_advance():
    game = make_game()
    for _ in range(50):
        game.tick(MockInput())
    game.tick(MockInput([Action.PAUSE]))
    before = world_snapshot(game)
    for _ in range(300):
        game.tick(MockInput())
    assert world_snapshot(game) == before


def test_paused_play_freezes_ralph_and_bricks():
    game = make_game()
    reach_play(game)
    for _ in range(200):
        game.tick(MockInput())
        if game.bricks.live_count:
            break
    assert game.bricks.live_count > 0
    game.tick(MockInput([Action.PAUSE]))
    before = world_snapshot(game)
    for _ in range(300):
        game.tick(MockInput())
    assert world_snapshot(game) == before

    game.tick(MockInput([Action.PAUSE]))
    game.tick(MockInput())
    assert world_snapshot(game) != before


def test_paused_game_ignores_movement_input():
    game = make_game()
    reach_play(game)
    game.tick(MockInput([Action.PAUSE]))
    column_before = game.felix.column
    game.tick(MockInput([Action.RIGHT]))
    for _ in range(60):
        game.tick(MockInput())
    assert game.felix.column == column_before


def test_focus_loss_pauses_but_never_unpauses():
    game = make_game()
    game.tick(MockInput(has_lost_focus=True))
    assert game.is_paused
    game.tick(MockInput(has_lost_focus=True))
    assert game.is_paused


def test_paused_draw_renders():
    game = make_game()
    game.tick(MockInput([Action.PAUSE]))
    surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
    game.draw(surface, alpha=0.3)
