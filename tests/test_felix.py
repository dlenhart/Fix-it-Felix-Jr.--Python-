import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()

from entities.felix import Felix, FelixState
from constants import BONUS_LIFE_THRESHOLD
from entities.building import Building


class MockInput:
    def __init__(self):
        self._just = set()

    def is_just_pressed(self, action):
        return action in self._just

    def is_pressed(self, action):
        return action in self._just


def test_initial_state():
    f = Felix()
    assert f.col == 2
    assert f.row == 0
    assert f.state == FelixState.IDLE
    assert f.lives == 10
    assert f.score == 0


def test_stun_costs_life():
    f = Felix()
    b = Building()
    b.reset_for_level(1)
    f.tick(MockInput(), b)
    f.stun()
    assert f.state == FelixState.STUNNED
    assert f.lives == 9


def test_super_prevents_stun():
    f = Felix()
    f.activate_super()
    f.stun()
    assert f.state != FelixState.STUNNED
    assert f.lives == 10


def test_score_bonus_life():
    f = Felix()
    initial = f.lives
    f.add_score(BONUS_LIFE_THRESHOLD)
    assert f.lives == initial + 1


def test_move_within_bounds():
    from input_handler import Action
    f = Felix()
    b = Building()
    b.reset_for_level(1)
    inp = MockInput()
    inp._just = {Action.RIGHT}
    f.tick(inp, b)
    assert f.state == FelixState.WALK_HORIZONTAL


def test_move_blocked_at_edge():
    from input_handler import Action
    f = Felix()
    f.col = 0
    b = Building()
    b.reset_for_level(1)
    inp = MockInput()
    inp._just = {Action.LEFT}
    f.tick(inp, b)
    assert f.state == FelixState.IDLE


def test_hammer_triggers():
    from input_handler import Action
    f = Felix()
    b = Building()
    b.reset_for_level(1)
    inp = MockInput()
    inp._just = {Action.JUMP}
    f.tick(inp, b)
    assert f.state == FelixState.HAMMERING


def test_stun_recovery():
    f = Felix()
    b = Building()
    b.reset_for_level(1)
    f.tick(MockInput(), b)
    f.stun()
    for _ in range(30):
        f.tick(MockInput(), b)
    assert f.state == FelixState.IDLE


if __name__ == "__main__":
    test_initial_state()
    test_stun_costs_life()
    test_super_prevents_stun()
    test_score_bonus_life()
    test_move_within_bounds()
    test_move_blocked_at_edge()
    test_hammer_triggers()
    test_stun_recovery()
    print("All Felix tests passed!")
