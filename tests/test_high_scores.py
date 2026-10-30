import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from scenes import high_score_scene  # noqa: E402


def test_default_high_scores_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(tmp_path / "scores.dat"))
    scores = high_score_scene.load_scores()
    assert [(entry["name"], entry["score"]) for entry in scores] == [
        ("VAV", 15000), ("DES", 10000), ("RYS", 8000), ("KYL", 6000), ("CMI", 4000)]


def test_saved_scores_replace_the_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(tmp_path / "scores.dat"))
    saved = [{"name": "ABC", "score": 99}]
    high_score_scene.save_scores(saved)
    assert high_score_scene.load_scores() == saved


class PressOnce:
    """Input handler stub: the given actions are just pressed on this tick only."""

    def __init__(self, *actions):
        self._actions = set(actions)

    def is_just_pressed(self, action):
        return action in self._actions


def entry_scene(tmp_path, monkeypatch, final_score=20000):
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(tmp_path / "scores.dat"))
    return high_score_scene.HighScoreScene(None, final_score)


def press(scene, *actions):
    scene.tick(PressOnce(*actions))


def test_entry_steps_from_the_displayed_a(tmp_path, monkeypatch):
    from input_handler import Action
    scene = entry_scene(tmp_path, monkeypatch)
    press(scene, Action.DOWN)
    assert scene._initials[0] == "B"
    press(scene, Action.UP)
    press(scene, Action.UP)
    assert scene._initials[0] == " "  # the space sits just before A


def test_confirm_puts_the_next_slot_back_on_a(tmp_path, monkeypatch):
    from input_handler import Action
    scene = entry_scene(tmp_path, monkeypatch)
    press(scene, Action.DOWN)
    press(scene, Action.DOWN)
    press(scene, Action.JUMP)
    press(scene, Action.DOWN)
    assert scene._initials[:2] == ["C", "B"]


def test_enter_or_space_confirms_and_the_third_saves(tmp_path, monkeypatch):
    from input_handler import Action
    scene = entry_scene(tmp_path, monkeypatch)
    press(scene, Action.START)
    press(scene, Action.JUMP)
    press(scene, Action.DOWN)
    press(scene, Action.START)
    saved = high_score_scene.load_scores()
    assert saved[0] == {"name": "AAB", "score": 20000}


def test_current_letter_flashes_15_ticks_red_17_white(tmp_path, monkeypatch):
    scene = entry_scene(tmp_path, monkeypatch)
    rows = []
    for _ in range(32):
        rows.append(scene.letter_color_row(0))
        press(scene)
    assert rows == [1] * 15 + [0] * 17
    assert scene.letter_color_row(1) == 1 and scene.letter_color_row(2) == 1


def test_draw_renders_the_entry(tmp_path, monkeypatch):
    import pygame
    scene = entry_scene(tmp_path, monkeypatch)
    scene.draw(pygame.Surface((240, 320)))
