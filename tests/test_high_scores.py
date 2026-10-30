import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from scenes import high_score_scene  # noqa: E402


def test_default_high_scores_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(tmp_path / "scores.dat"))
    scores = high_score_scene.load_scores()
    assert [entry["score"] for entry in scores] == [15000, 10000, 8000, 6000, 4000]
    assert all(entry["name"].strip() == "" for entry in scores)


def test_saved_scores_replace_the_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(tmp_path / "scores.dat"))
    saved = [{"name": "ABC", "score": 99}]
    high_score_scene.save_scores(saved)
    assert high_score_scene.load_scores() == saved
