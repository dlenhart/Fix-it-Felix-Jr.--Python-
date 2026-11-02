import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame  # noqa: E402
import pytest  # noqa: E402

import sound_manager  # noqa: E402
from sound_manager import SoundManager  # noqa: E402


class RecordingMusic:
    """Stands in for pygame.mixer.music and logs which files it loads."""

    def __init__(self):
        self.loaded = []

    def load(self, path):
        self.loaded.append(os.path.basename(path))

    def play(self, loops=0):
        pass

    def stop(self):
        pass


@pytest.fixture
def sound(monkeypatch):
    pygame.init()
    manager = SoundManager()
    music = RecordingMusic()
    monkeypatch.setattr(sound_manager.pygame.mixer, "music", music)
    yield manager, music
    pygame.quit()


def test_music_index_already_current_is_not_restarted(sound):
    # FUN_0040f4a0 returns at once when ESI is already DAT_00419cb0.
    manager, music = sound
    manager.play_music_index(14, is_looping=True)
    manager.play_music_index(14, is_looping=True)
    assert music.loaded == ["sound14.wav"]


def test_other_music_replaces_it_and_it_restarts_after(sound):
    manager, music = sound
    manager.play_music_index(14, is_looping=True)
    manager.play_music_index(22, is_looping=False)
    manager.play_music_index(14, is_looping=True)
    assert music.loaded == ["sound14.wav", "sound22.wav", "sound14.wav"]


def test_stopping_or_named_music_clears_the_current_index(sound):
    manager, music = sound
    manager.play_music_index(14, is_looping=True)
    manager.stop_music()
    manager.play_music_index(14, is_looping=True)
    manager.play_music("title")
    manager.play_music_index(14, is_looping=True)
    assert music.loaded == ["sound14.wav", "sound14.wav", "sound9.wav", "sound14.wav"]


def test_missing_music_file_raises(sound, monkeypatch):
    manager, _ = sound
    monkeypatch.setattr(sound_manager, "ASSET_DIR", "/nonexistent")
    with pytest.raises(FileNotFoundError):
        manager.play_music_index(14, is_looping=True)
