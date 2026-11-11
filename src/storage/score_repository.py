"""Persistence for the high-score table (Repository pattern)."""

import json
import os

from constants.high_scores import DEFAULT_HIGH_SCORES, LETTER_OPTIONS


class CorruptScoresError(ValueError):
    """The scores file exists but is not a valid high-score table."""


def default_scores():
    """The table shown before anyone has played."""
    return [{"name": name, "score": score} for name, score in DEFAULT_HIGH_SCORES]


class ScoreRepository:
    """Loads and saves the high-score table as JSON at one file path."""

    def __init__(self, path: str):
        self._path = path

    def load(self):
        """The saved table, or the default table when no file exists yet.

        Raises CorruptScoresError when the file is not a valid table, so a damaged
        file is never silently replaced by the next save. An unreadable file
        raises the OSError from open().
        """
        if not os.path.exists(self._path):
            return default_scores()
        with open(self._path, "r") as f:
            try:
                scores = json.load(f)
            except json.JSONDecodeError as error:
                raise self._corrupt(f"not valid JSON ({error})") from error
        self._validate(scores)
        return scores

    def save(self, scores) -> None:
        self._validate(scores)
        with open(self._path, "w") as f:
            json.dump(scores, f, indent=2)

    def _validate(self, scores) -> None:
        if not isinstance(scores, list):
            raise self._corrupt("the table is not a list")
        for entry in scores:
            if not isinstance(entry, dict) or set(entry) != {"name", "score"}:
                raise self._corrupt(f"entry {entry!r} is not {{name, score}}")
            name, score = entry["name"], entry["score"]
            if not isinstance(name, str) or any(letter not in LETTER_OPTIONS for letter in name):
                raise self._corrupt(f"name {name!r} has letters outside {LETTER_OPTIONS!r}")
            if not isinstance(score, int) or isinstance(score, bool) or score < 0:
                raise self._corrupt(f"score {score!r} is not a non-negative integer")

    def _corrupt(self, reason: str) -> CorruptScoresError:
        return CorruptScoresError(f"{self._path}: {reason}; fix or delete the file")
