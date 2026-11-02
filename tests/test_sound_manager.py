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


def test_stopping_the_current_musics_index_stops_the_music(sound, monkeypatch):
    manager, music = sound
    stopped = []
    monkeypatch.setattr(music, "stop", lambda: stopped.append(True), raising=False)
    manager.play_music_index(22, is_looping=False)
    manager.stop_sound_index(22)
    assert stopped == [True]
    manager.stop_sound_index(5)
    assert stopped == [True]


def test_every_mapped_sound_file_exists():
    for filename in list(sound_manager.SOUND_MAP.values()) + list(sound_manager.MUSIC_MAP.values()):
        assert os.path.exists(os.path.join(sound_manager.ASSET_DIR, f"{filename}.wav")), filename


def test_unknown_music_name_loads_nothing(sound):
    manager, music = sound
    manager.play_music("no_such_music")
    assert music.loaded == []


def test_missing_sound_index_raises_instead_of_staying_silent(sound):
    manager, _ = sound
    missing_index = 9999
    with pytest.raises(FileNotFoundError):
        manager.play_sound_index(missing_index)
    with pytest.raises(FileNotFoundError):
        manager.restart_sound_index(missing_index)
    with pytest.raises(FileNotFoundError):
        manager.stop_sound_index(missing_index)


def test_pause_and_resume_reach_the_music_channel(sound, monkeypatch):
    manager, music = sound
    calls = []
    monkeypatch.setattr(music, "pause", lambda: calls.append("pause"), raising=False)
    monkeypatch.setattr(music, "unpause", lambda: calls.append("unpause"), raising=False)
    manager.pause_all()
    manager.resume_all()
    assert calls == ["pause", "unpause"]


def test_music_volume_is_forwarded(sound, monkeypatch):
    manager, music = sound
    volumes = []
    monkeypatch.setattr(music, "set_volume", volumes.append, raising=False)
    manager.set_music_volume(0.25)
    assert volumes == [0.25]
