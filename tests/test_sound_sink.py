import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from audio.sound_manager import SoundManager  # noqa: E402
from audio.sound_sink import SILENT_SOUND, SilentSound, SoundSink  # noqa: E402

PROTOCOL_METHODS = {name for name, _ in inspect.getmembers(SoundSink, inspect.isfunction)
                    if not name.startswith("_")}


def test_the_protocol_names_every_call_gameplay_makes():
    assert PROTOCOL_METHODS == {"play_sfx", "play_sound_index", "restart_sound_index",
                                "stop_sound_index", "play_music_index"}


def parameter_names(function):
    return list(inspect.signature(function).parameters)


def test_sound_manager_and_silent_sound_both_satisfy_the_protocol():
    for implementation in (SoundManager, SilentSound):
        for name in PROTOCOL_METHODS:
            expected = parameter_names(getattr(SoundSink, name))
            assert parameter_names(getattr(implementation, name)) == expected, (implementation, name)


def test_silent_sound_does_nothing():
    for name in PROTOCOL_METHODS:
        parameters = list(inspect.signature(getattr(SilentSound, name)).parameters)[1:]
        assert getattr(SILENT_SOUND, name)(*[0] * len(parameters)) is None
