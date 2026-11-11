"""What gameplay code may ask of the audio system, and a do-nothing stand-in.

SoundSink is the interface the entities and phases depend on (SoundManager
satisfies it structurally). SilentSound is a Null Object: passing it means
"make no sound", so callers never branch on whether a sound system exists.
"""

from typing import Protocol


class SoundSink(Protocol):
    def play_sfx(self, name: str) -> None:
        """Play a named effect from constants.sounds.SOUND_MAP."""

    def play_sound_index(self, index: int) -> None:
        """Play the exe's sound index once."""

    def restart_sound_index(self, index: int) -> None:
        """Play the exe's sound index from the start, cutting off a copy still playing."""

    def stop_sound_index(self, index: int) -> None:
        """Stop every playing copy of the exe's sound index."""

    def play_music_index(self, index: int, is_looping: bool) -> None:
        """Replace the current music with the exe's sound index."""


class SilentSound:
    """A SoundSink that plays nothing."""

    def play_sfx(self, name: str) -> None:
        pass

    def play_sound_index(self, index: int) -> None:
        pass

    def restart_sound_index(self, index: int) -> None:
        pass

    def stop_sound_index(self, index: int) -> None:
        pass

    def play_music_index(self, index: int, is_looping: bool) -> None:
        pass


SILENT_SOUND = SilentSound()
