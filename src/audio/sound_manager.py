import os

import pygame

from constants.sounds import MUSIC_MAP, SOUND_FILE_PREFIX, SOUND_MAP
from paths import ASSET_DIR


def _sound_index(filename):
    """The exe sound index in a "soundN" file name."""
    return int(filename[len(SOUND_FILE_PREFIX):])


def _sound_path(index):
    return os.path.join(ASSET_DIR, f"{SOUND_FILE_PREFIX}{index}.wav")


class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        # One Sound per exe index, shared by the by-name and by-index calls, so
        # stop_sound_index stops a sound however it was started.
        self._sounds_by_index = {}
        # [EXE] DAT_00419cb0: the music index FUN_0040f4a0 last started (None = none).
        self._current_music_index = None
        self._load_sounds()

    def _load_sounds(self):
        for filename in SOUND_MAP.values():
            index = _sound_index(filename)
            if os.path.exists(_sound_path(index)):
                self._sounds_by_index[index] = pygame.mixer.Sound(_sound_path(index))

    def play_sfx(self, name):
        filename = SOUND_MAP.get(name)
        if not filename:
            return
        sound = self._sounds_by_index.get(_sound_index(filename))
        if sound:
            sound.play()

    def play_music(self, name, loop=True):
        filename = MUSIC_MAP.get(name)
        if not filename:
            return
        path = os.path.join(ASSET_DIR, f"{filename}.wav")
        if os.path.exists(path):
            pygame.mixer.music.load(path)
            loops = -1 if loop else 0
            pygame.mixer.music.play(loops)
            self._current_music_index = _sound_index(filename)

    def play_sound_index(self, index):
        """Play the exe's sound index (soundN.wav), as FUN_004100d0 does for one-shot effects.

        Raises FileNotFoundError when the wav is missing.
        """
        self._indexed_sound(index).play()

    def restart_sound_index(self, index):
        """Play the exe's sound index from the start, cutting off a copy still playing.

        FUN_0040d970 / FUN_0040dd90 rewind the sound's own buffer (position 0,
        playing 1) rather than starting a second copy.
        Raises FileNotFoundError when the wav is missing.
        """
        sound = self._indexed_sound(index)
        sound.stop()
        sound.play()

    def stop_sound_index(self, index):
        """Stop every playing copy of the exe's sound index (FUN_00410140).

        The exe's music is one of the same sound buffers, so this also stops the
        music when it is that index (the current-music index stays set, as in
        the exe). Raises FileNotFoundError when the wav is missing.
        """
        self._indexed_sound(index).stop()
        if index == self._current_music_index:
            pygame.mixer.music.stop()

    def play_music_index(self, index, is_looping):
        """Replace the current music with the exe's sound index.

        FUN_0040f4a0 takes the index in ESI and the loop flag as its argument,
        and does nothing when that index is already the current music
        (DAT_00419cb0), even if a one-shot track has finished.
        Raises FileNotFoundError when the wav is missing.
        """
        if index == self._current_music_index:
            return
        path = _sound_path(index)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(-1 if is_looping else 0)
        self._current_music_index = index

    def _indexed_sound(self, index):
        if index in self._sounds_by_index:
            return self._sounds_by_index[index]
        path = _sound_path(index)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        sound = pygame.mixer.Sound(path)
        self._sounds_by_index[index] = sound
        return sound

    def stop_music(self):
        pygame.mixer.music.stop()
        self._current_music_index = None

    def pause_all(self):
        """Freeze music and any in-flight sound effects where they are."""
        pygame.mixer.music.pause()
        pygame.mixer.pause()

    def resume_all(self):
        pygame.mixer.music.unpause()
        pygame.mixer.unpause()

    def set_sfx_volume(self, volume):
        for sound in self._sounds_by_index.values():
            sound.set_volume(volume)

    def set_music_volume(self, volume):
        pygame.mixer.music.set_volume(volume)
