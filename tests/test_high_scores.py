import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest  # noqa: E402

from controls.action import Action  # noqa: E402
from constants.high_scores import INITIALS_LENGTH, MAX_SCORES  # noqa: E402
from scenes import high_score_scene  # noqa: E402
from storage.score_repository import CorruptScoresError, ScoreRepository  # noqa: E402


def test_default_high_scores_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(tmp_path / "scores.dat"))
    scores = ScoreRepository(high_score_scene.SCORES_FILE).load()
    assert [(entry["name"], entry["score"]) for entry in scores] == [
        ("VAV", 15000), ("DES", 10000), ("RYS", 8000), ("KYL", 6000), ("CMI", 4000)]


def test_saved_scores_replace_the_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(tmp_path / "scores.dat"))
    saved = [{"name": "ABC", "score": 99}]
    ScoreRepository(high_score_scene.SCORES_FILE).save(saved)
    assert ScoreRepository(high_score_scene.SCORES_FILE).load() == saved


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
    from controls.action import Action
    scene = entry_scene(tmp_path, monkeypatch)
    press(scene, Action.DOWN)
    assert scene.initials[0] == "B"
    press(scene, Action.UP)
    press(scene, Action.UP)
    assert scene.initials[0] == " "  # the space sits just before A


def test_confirm_puts_the_next_slot_back_on_a(tmp_path, monkeypatch):
    from controls.action import Action
    scene = entry_scene(tmp_path, monkeypatch)
    press(scene, Action.DOWN)
    press(scene, Action.DOWN)
    press(scene, Action.JUMP)
    press(scene, Action.DOWN)
    assert scene.initials[:2] == ("C", "B")


def test_enter_or_space_confirms_and_the_third_saves(tmp_path, monkeypatch):
    from controls.action import Action
    scene = entry_scene(tmp_path, monkeypatch)
    press(scene, Action.START)
    press(scene, Action.JUMP)
    press(scene, Action.DOWN)
    press(scene, Action.START)
    saved = ScoreRepository(high_score_scene.SCORES_FILE).load()
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
    ScoreRepository(high_score_scene.SCORES_FILE).save(table)
    assert ScoreRepository(high_score_scene.SCORES_FILE).load() == table


def test_scores_capped_at_max_and_sorted_descending(tmp_path, monkeypatch):
    from controls.action import Action
    scene = entry_scene(tmp_path, monkeypatch, final_score=7000)
    for _ in range(INITIALS_LENGTH):
        press(scene, Action.JUMP)
    saved = ScoreRepository(high_score_scene.SCORES_FILE).load()
    assert len(saved) == MAX_SCORES
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
    from controls.action import Action
    from scenes.title_scene import TitleScene
    scene, manager = display_scene(tmp_path, monkeypatch)
    press(scene)
    assert manager.replaced_with == []
    press(scene, Action.START)
    assert len(manager.replaced_with) == 1
    assert isinstance(manager.replaced_with[0], TitleScene)


def test_table_times_out_to_the_title(tmp_path, monkeypatch):
    from constants.high_scores import HS_DISPLAY_TIMER_TICKS
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


def test_corrupt_scores_file_raises_and_is_left_untouched(tmp_path):
    scores_file = tmp_path / "scores.dat"
    scores_file.write_text("{not json")
    with pytest.raises(CorruptScoresError, match="not valid JSON"):
        ScoreRepository(str(scores_file)).load()
    assert scores_file.read_text() == "{not json"


@pytest.mark.parametrize("table, reason", [
    ({"name": "AAA", "score": 1}, "not a list"),
    ([{"name": "AAA"}], "is not {name, score}"),
    ([{"name": "AAA", "score": 1, "extra": 2}], "is not {name, score}"),
    ([{"name": "a~a", "score": 1}], "letters outside"),
    ([{"name": 7, "score": 1}], "letters outside"),
    ([{"name": "AAA", "score": "100"}], "non-negative integer"),
    ([{"name": "AAA", "score": -5}], "non-negative integer"),
    ([{"name": "AAA", "score": True}], "non-negative integer"),
])
def test_a_scores_file_that_is_not_a_valid_table_raises(tmp_path, table, reason):
    scores_file = tmp_path / "scores.dat"
    scores_file.write_text(json.dumps(table))
    with pytest.raises(CorruptScoresError, match=reason):
        ScoreRepository(str(scores_file)).load()


def test_save_refuses_an_invalid_table(tmp_path):
    scores_file = tmp_path / "scores.dat"
    with pytest.raises(CorruptScoresError):
        ScoreRepository(str(scores_file)).save([{"name": "AAA", "score": -1}])
    assert not scores_file.exists()


def test_the_high_score_scene_raises_on_a_corrupt_file(tmp_path, monkeypatch):
    (tmp_path / "scores.dat").write_text("[1, 2]")  # entry_scene points SCORES_FILE here
    with pytest.raises(CorruptScoresError):
        entry_scene(tmp_path, monkeypatch, final_score=100)


def test_an_injected_repository_is_used_for_load_and_save(tmp_path):
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    repository = ScoreRepository(str(tmp_path / "elsewhere.dat"))
    scene = high_score_scene.HighScoreScene(None, 20000, score_repository=repository)
    for _ in range(INITIALS_LENGTH):
        press(scene, Action.JUMP)
    assert repository.load()[0] == {"name": "AAA", "score": 20000}
