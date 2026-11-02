import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scene_manager import Scene, SceneManager  # noqa: E402


class RecordingScene(Scene):
    def __init__(self, name, log):
        super().__init__(None)
        self.name = name
        self.log = log

    def on_enter(self):
        self.log.append((self.name, "enter"))

    def on_exit(self):
        self.log.append((self.name, "exit"))

    def tick(self, input_handler):
        self.log.append((self.name, "tick", input_handler))

    def draw(self, screen, alpha=1.0):
        self.log.append((self.name, "draw", screen, alpha))


def test_empty_manager_has_no_current_and_ignores_tick_and_draw():
    manager = SceneManager()
    manager.tick(None)
    manager.draw(None)
    manager.pop()
    assert manager.current is None


def test_push_calls_on_enter_and_becomes_current():
    log = []
    manager = SceneManager()
    first, second = RecordingScene("a", log), RecordingScene("b", log)
    manager.push(first)
    manager.push(second)
    assert manager.current is second
    assert log == [("a", "enter"), ("a", "exit"), ("b", "enter")]


def test_replace_calls_on_exit_then_on_enter():
    log = []
    manager = SceneManager()
    first, second = RecordingScene("a", log), RecordingScene("b", log)
    manager.push(first)
    log.clear()
    manager.replace(second)
    assert log == [("a", "exit"), ("b", "enter")]
    assert manager.current is second


def test_replace_on_empty_manager_just_enters():
    log = []
    manager = SceneManager()
    scene = RecordingScene("a", log)
    manager.replace(scene)
    assert manager.current is scene
    assert log == [("a", "enter")]


def test_pop_returns_to_previous_scene():
    log = []
    manager = SceneManager()
    first, second = RecordingScene("a", log), RecordingScene("b", log)
    manager.push(first)
    manager.push(second)
    log.clear()
    manager.pop()
    assert manager.current is first
    assert log == [("b", "exit"), ("a", "enter")]


def test_tick_and_draw_go_to_current_scene_only():
    log = []
    manager = SceneManager()
    manager.push(RecordingScene("a", log))
    manager.push(RecordingScene("b", log))
    log.clear()
    manager.tick("input")
    manager.draw("screen", 0.25)
    assert log == [("b", "tick", "input"), ("b", "draw", "screen", 0.25)]


def test_base_scene_hooks_are_harmless_no_ops():
    scene = Scene(None)
    assert scene.tick(None) is None
    assert scene.draw(None) is None
    assert scene.on_enter() is None
    assert scene.on_exit() is None
