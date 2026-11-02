import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest  # noqa: E402

from input_handler import Action  # noqa: E402
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
    assert scene.initials[0] == "B"
    press(scene, Action.UP)
    press(scene, Action.UP)
    assert scene.initials[0] == " "  # the space sits just before A


def test_confirm_puts_the_next_slot_back_on_a(tmp_path, monkeypatch):
    from input_handler import Action
    scene = entry_scene(tmp_path, monkeypatch)
    press(scene, Action.DOWN)
    press(scene, Action.DOWN)
    press(scene, Action.JUMP)
    press(scene, Action.DOWN)
    assert scene.initials[:2] == ("C", "B")


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


def test_save_then_load_round_trips(tmp_path, monkeypatch):
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(tmp_path / "scores.dat"))
    table = [{"name": "AAA", "score": 300}, {"name": "BBB", "score": 200},
             {"name": "CCC", "score": 100}]
    high_score_scene.save_scores(table)
    assert high_score_scene.load_scores() == table


def test_scores_capped_at_max_and_sorted_descending(tmp_path, monkeypatch):
    from input_handler import Action
    scene = entry_scene(tmp_path, monkeypatch, final_score=7000)
    for _ in range(high_score_scene.INITIALS_LENGTH):
        press(scene, Action.JUMP)
    saved = high_score_scene.load_scores()
    assert len(saved) == high_score_scene.MAX_SCORES
    scores = [entry["score"] for entry in saved]
    assert scores == [15000, 10000, 8000, 7000, 6000]  # 4000 fell off the bottom
    assert saved[3]["name"] == "AAA"


class RecordingManager:
    def __init__(self):
        self.replaced_with = []

    def replace(self, scene):
        self.replaced_with.append(scene)


def display_scene(tmp_path, monkeypatch, final_score=0):
    entry_scene(tmp_path, monkeypatch)  # initialises pygame and points SCORES_FILE at tmp_path
    manager = RecordingManager()
    return high_score_scene.HighScoreScene(manager, final_score), manager


def test_score_below_the_table_skips_initials_and_saves_nothing(tmp_path, monkeypatch):
    scene, manager = display_scene(tmp_path, monkeypatch, final_score=100)
    press(scene, Action.JUMP)  # would only confirm a letter if the entry were open
    assert len(manager.replaced_with) == 1
    assert not os.path.exists(tmp_path / "scores.dat")


def test_pressing_start_on_the_table_returns_to_the_title(tmp_path, monkeypatch):
    from input_handler import Action
    from scenes.title_scene import TitleScene
    scene, manager = display_scene(tmp_path, monkeypatch)
    press(scene)
    assert manager.replaced_with == []
    press(scene, Action.START)
    assert len(manager.replaced_with) == 1
    assert isinstance(manager.replaced_with[0], TitleScene)


def test_table_times_out_to_the_title(tmp_path, monkeypatch):
    from constants import HS_DISPLAY_TIMER_TICKS
    scene, manager = display_scene(tmp_path, monkeypatch)
    for _ in range(HS_DISPLAY_TIMER_TICKS - 1):
        press(scene)
    assert manager.replaced_with == []
    press(scene)
    assert len(manager.replaced_with) == 1


def test_draw_renders_the_table_without_entry(tmp_path, monkeypatch):
    import pygame
    scene, _ = display_scene(tmp_path, monkeypatch)
    screen = pygame.Surface((240, 320))
    scene.draw(screen)
    assert screen.get_bounding_rect().width > 0  # something other than black was drawn


def test_leaving_the_table_stops_the_music(tmp_path, monkeypatch):
    scene, _ = display_scene(tmp_path, monkeypatch)
    stopped = []
    monkeypatch.setattr(scene.sound, "stop_music", lambda: stopped.append(True))
    scene.on_exit()
    assert stopped == [True]


@pytest.mark.xfail(strict=True, reason="load_scores silently returns an empty table for a "
                                       "corrupt file; fail-fast says it should raise "
                                       "(TODO in high_score_scene.load_scores)")
def test_corrupt_scores_file_behavior(tmp_path, monkeypatch):
    scores_file = tmp_path / "scores.dat"
    scores_file.write_text("{not json")
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(scores_file))
    with pytest.raises(ValueError):
        high_score_scene.load_scores()
