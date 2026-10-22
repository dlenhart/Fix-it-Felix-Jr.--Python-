import os
import pygame
from constants import ASSET_DIR

SOUND_MAP = {
    "hammer_hit": "sound3",
    "hammer_hit_alt": "sound6",
    # Ghidra-confirmed: FUN_0040c3d0 case 5 (start of the jump up, FUN_0040bea0) plays index 0x0F.
    "jump": "sound15",
    # Ghidra-confirmed: FUN_0040c3d0 case 6 (start of the drop down, FUN_0040c0d0) plays index 0x11.
    "drop_down": "sound17",
    # Ghidra-confirmed: FUN_00409840 plays index 5 when it damages an intact window.
    "window_break": "sound5",
    # TODO: index 0x11 is the drop-down start (FUN_0040c3d0 case 6); no exe sound is
    # known for the hammer reaching full extension (case 8 plays none).
    "hammer_extended": "sound17",
    "pie_pickup": "sound16",
    "ralph_grunt": "sound1",
    "window_fixed": "sound4",
    "felix_catchphrase": "sound2",
    "ralph_catchphrase": "sound0",
    "super_felix": "sound25",
    "section_clear": "sound22",
    "score_bonus": "sound23",
    "pie_throw": "sound18",
    "level_transition": "sound13",
    "ralph_falling": "sound29",
    "bonus_life": "sound10",
    "game_over": "sound21",
    "menu_select": "sound26",
    "menu_confirm": "sound27",
    "bonus_score_alt": "sound28",
    # TODO: index 0x0F is the jump up (FUN_0040c3d0 case 5); the walk start (case 3)
    # plays nothing in the exe.
    "felix_move": "sound15",
    "death": "sound19",             # Ghidra-confirmed: index 0x13 = death/game over
}

MUSIC_MAP = {
    "cutscene_intro": "sound11",
    "level_clear": "sound12",
    "high_score": "sound24",
    "gameplay_a": "sound7",
    "gameplay_b": "sound8",
    "title": "sound9",
    "extended": "sound14",
}


class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        self._sounds = {}
        self._load_sounds()

    def _load_sounds(self):
        for name, filename in SOUND_MAP.items():
            path = os.path.join(ASSET_DIR, f"{filename}.wav")
            if os.path.exists(path):
                self._sounds[name] = pygame.mixer.Sound(path)

    def play_sfx(self, name):
        sound = self._sounds.get(name)
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

    def stop_music(self):
        pygame.mixer.music.stop()

    def pause_all(self):
        """Freeze music and any in-flight sound effects where they are."""
        pygame.mixer.music.pause()
        pygame.mixer.pause()

    def resume_all(self):
        pygame.mixer.music.unpause()
        pygame.mixer.unpause()

    def set_sfx_volume(self, volume):
        for sound in self._sounds.values():
            sound.set_volume(volume)

    def set_music_volume(self, volume):
        pygame.mixer.music.set_volume(volume)
