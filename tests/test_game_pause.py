import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from constants import GAME_WIDTH, GAME_HEIGHT
from input_handler import Action
from scene_manager import SceneManager
from scenes.game_scene import GameScene


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


def make_game():
    manager = SceneManager()
    game = GameScene(manager)
    manager.push(game)
    return game


def snapshot(game):
    return (game.ralph.throw_ticks, game._pie_ticks,
            [(brick.x, brick.y) for brick in game.bricks])


def test_pause_key_toggles():
    for pause_action in (Action.START, Action.PAUSE):
        game = make_game()
        game.tick(MockInput([pause_action]))
        assert game._is_paused
        game.tick(MockInput([pause_action]))
        assert not game._is_paused


def test_paused_game_does_not_advance():
    game = make_game()
    for _ in range(200):
        game.tick(MockInput())
    game.tick(MockInput([Action.PAUSE]))
    before = snapshot(game)
    for _ in range(300):
        game.tick(MockInput())
    assert snapshot(game) == before


def test_paused_game_ignores_movement_input():
    game = make_game()
    game.tick(MockInput())
    game.tick(MockInput([Action.PAUSE]))
    col_before = game.felix.col
    game.tick(MockInput([Action.RIGHT]))
    for _ in range(60):
        game.tick(MockInput())
    assert game.felix.col == col_before


def test_focus_loss_pauses_but_never_unpauses():
    game = make_game()
    game.tick(MockInput(has_lost_focus=True))
    assert game._is_paused
    game.tick(MockInput(has_lost_focus=True))
    assert game._is_paused


def test_paused_draw_renders():
    game = make_game()
    game.tick(MockInput([Action.PAUSE]))
    surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
    game.draw(surface, alpha=0.3)


if __name__ == "__main__":
    test_pause_key_toggles()
    test_paused_game_does_not_advance()
    test_paused_game_ignores_movement_input()
    test_focus_loss_pauses_but_never_unpauses()
    test_paused_draw_renders()
    print("All pause tests passed!")
