import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from scenes.game.play_tick_pipeline import PlayTickPipeline  # noqa: E402
from test_game_flow import MockInput, make_game, reach_play, spawn_brick_on_felix, tick_until  # noqa: E402


def record_calls(monkeypatch, target, method_name, log, label):
    original = getattr(target, method_name)

    def recording(*args, **kwargs):
        log.append(label)
        return original(*args, **kwargs)
    monkeypatch.setattr(target, method_name, recording)


class RecordingHook(PlayTickPipeline):
    def __init__(self, log, next_phase=None):
        self._log = log
        self._next_phase = next_phase

    def after_felix(self, game, felix_events):
        self._log.append("hook")
        return self._next_phase


def test_after_felix_runs_between_felix_and_ralph(monkeypatch):
    _, game = make_game()
    reach_play(game)
    game.input_handler = MockInput()
    log = []
    record_calls(monkeypatch, game.felix, "tick", log, "felix")
    record_calls(monkeypatch, game.ralph, "tick", log, "ralph")
    record_calls(monkeypatch, game.bricks, "tick", log, "bricks")
    record_calls(monkeypatch, game.hazards, "tick", log, "hazards")
    assert RecordingHook(log).run(game) is None
    assert log == ["felix", "hook", "ralph", "bricks", "hazards"]


def test_a_phase_from_after_felix_ends_the_tick_before_ralph(monkeypatch):
    _, game = make_game()
    reach_play(game)
    game.input_handler = MockInput()
    log = []
    record_calls(monkeypatch, game.ralph, "tick", log, "ralph")
    next_phase = object()
    assert RecordingHook(log, next_phase).run(game) is next_phase
    assert log == ["hook"]


def test_the_hit_freeze_skips_the_hook_and_everything_after_felix(monkeypatch):
    _, game = make_game()
    reach_play(game)
    spawn_brick_on_felix(game)
    tick_until(game, lambda: game.felix.is_in_hit_sequence)
    game.input_handler = MockInput()
    log = []
    record_calls(monkeypatch, game.ralph, "tick", log, "ralph")
    assert RecordingHook(log).run(game) is None
    assert log == []


def test_a_respawn_restarts_the_patrol_and_resets_the_birds_once(monkeypatch):
    _, game = make_game()
    reach_play(game)
    spawn_brick_on_felix(game)
    tick_until(game, lambda: game.felix.is_in_hit_sequence)
    log = []
    record_calls(monkeypatch, game.ralph, "restart_patrol", log, "restart_patrol")
    record_calls(monkeypatch, game.hazards, "reset_birds", log, "reset_birds")
    tick_until(game, lambda: not game.felix.is_in_hit_sequence)
    for _ in range(30):
        game.tick(MockInput())
    assert log == ["restart_patrol", "reset_birds"]
