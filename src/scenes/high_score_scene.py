import json
import os
import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK, PROJECT_ROOT, HS_DISPLAY_TIMER_TICKS
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer, scale_text_to_fit

SCORES_FILE = os.path.join(PROJECT_ROOT, "scores.dat")
MAX_SCORES = 5                # Ghidra-confirmed: 5 entries
INITIALS_LENGTH = 3           # Ghidra-confirmed: 3 chars
# [EXE] FUN_00408fc0 case 8 starts the entry on "A" (index 1, after the space), and
# FUN_00407f50 puts each next slot back on index 1 when a letter is confirmed.
FIRST_LETTER_INDEX = 1
# [EXE] FUN_00408280 draws the entry's letters in font row 1 (red) and flashes the
# current one to row 0 (white) while (frame counter & 0x1f) >= 0xf: 15 ticks red,
# then 17 white.
INITIALS_COLOR_ROW = 1
CURRENT_LETTER_FLASH_COLOR_ROW = 0
CURRENT_LETTER_FLASH_PERIOD_MASK = 0x1F
CURRENT_LETTER_FLASH_START_TICK = 0xF
# Ghidra-confirmed: 38 characters including space, A-Z, 0-9, period
LETTER_OPTIONS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."


# [EXE] FUN_0040a060 seeds the table with these names (string table 0x419e68) and
# scores; both the scores and the names are from the exe.
DEFAULT_HIGH_SCORES = [
    ("VAV", 15000),
    ("DES", 10000),
    ("RYS", 8000),
    ("KYL", 6000),
    ("CMI", 4000),
]


def default_scores():
    """The table shown before anyone has played."""
    return [{"name": name, "score": score} for name, score in DEFAULT_HIGH_SCORES]


def load_scores():
    if not os.path.exists(SCORES_FILE):
        return default_scores()
    try:
        with open(SCORES_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_scores(scores):
    with open(SCORES_FILE, "w") as f:
        json.dump(scores, f, indent=2)


class HighScoreScene(Scene):
    def __init__(self, manager, final_score=0):
        super().__init__(manager)
        self.final_score = final_score
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self.scores = load_scores()

        self._is_entering = self._qualifies()
        self._initials = ["A", "A", "A"]
        self._cursor = 0
        self._letter_index = FIRST_LETTER_INDEX
        self._display_ticks = 0
        self._flash_ticks = 0

    def _qualifies(self):
        if self.final_score <= 0:
            return False
        if len(self.scores) < MAX_SCORES:
            return True
        return self.final_score > self.scores[-1]["score"]

    # [EXE] initials entry (state 8, FUN_00407f50) plays no music or sounds.
    def on_exit(self):
        self.sound.stop_music()

    def tick(self, input_handler):
        """One game tick (1/60s). All game logic is tick-counted."""
        if self._is_entering:
            self._flash_ticks += 1
            if input_handler.is_just_pressed(Action.UP):
                self._letter_index = (self._letter_index - 1) % len(LETTER_OPTIONS)
                self._initials[self._cursor] = LETTER_OPTIONS[self._letter_index]
            elif input_handler.is_just_pressed(Action.DOWN):
                self._letter_index = (self._letter_index + 1) % len(LETTER_OPTIONS)
                self._initials[self._cursor] = LETTER_OPTIONS[self._letter_index]
            # [USER] ENTER confirms as well as SPACE.
            elif (input_handler.is_just_pressed(Action.JUMP) or
                    input_handler.is_just_pressed(Action.START)):
                self._cursor += 1
                self._letter_index = FIRST_LETTER_INDEX
                if self._cursor >= INITIALS_LENGTH:
                    self._save_score()
                    self._is_entering = False
        else:
            if (input_handler.is_just_pressed(Action.START) or
                    input_handler.is_just_pressed(Action.JUMP)):
                from scenes.title_scene import TitleScene
                self.manager.replace(TitleScene(self.manager))
                return

        if not self._is_entering:
            self._display_ticks += 1
            if self._display_ticks >= HS_DISPLAY_TIMER_TICKS:
                from scenes.title_scene import TitleScene
                self.manager.replace(TitleScene(self.manager))

    def letter_color_row(self, slot):
        """Font row for an initials slot: the current one flashes, the others stay red."""
        if slot != self._cursor:
            return INITIALS_COLOR_ROW
        if (self._flash_ticks & CURRENT_LETTER_FLASH_PERIOD_MASK) < CURRENT_LETTER_FLASH_START_TICK:
            return INITIALS_COLOR_ROW
        return CURRENT_LETTER_FLASH_COLOR_ROW

    def _render_initials(self):
        letters = [self.font.render_text(letter, color_row=self.letter_color_row(slot))
                   for slot, letter in enumerate(self._initials)]
        letter_width, letter_height = letters[0].get_size()
        # One letter-wide gap between slots, as the old " ".join() spacing had.
        surface = pygame.Surface((letter_width * (2 * len(letters) - 1), letter_height),
                                 pygame.SRCALPHA)
        for slot, letter in enumerate(letters):
            surface.blit(letter, (slot * 2 * letter_width, 0))
        return surface

    def _save_score(self):
        name = "".join(self._initials)
        self.scores.append({"name": name, "score": self.final_score})
        self.scores.sort(key=lambda s: s["score"], reverse=True)
        self.scores = self.scores[:MAX_SCORES]
        save_scores(self.scores)

    def draw(self, screen, alpha=1.0):
        screen.fill(BLACK)

        header = self.font.render_text("HIGH SCORES", color_row=0)
        header_scaled = scale_text_to_fit(header, GAME_WIDTH - 16, preferred_scale=3.0)
        rect = header_scaled.get_rect(center=(GAME_WIDTH // 2, 40))
        screen.blit(header_scaled, rect)

        if self._is_entering:
            prompt = self.font.render_text("ENTER YOUR INITIALS", color_row=1)
            p_scaled = scale_text_to_fit(prompt, GAME_WIDTH - 16, preferred_scale=2.0)
            rect = p_scaled.get_rect(center=(GAME_WIDTH // 2, 90))
            screen.blit(p_scaled, rect)

            initials = self._render_initials()
            i_scaled = scale_text_to_fit(initials, GAME_WIDTH - 16, preferred_scale=3.0)
            rect = i_scaled.get_rect(center=(GAME_WIDTH // 2, 130))
            screen.blit(i_scaled, rect)

        col_header = self.font.render_text("NAME      SCORE", color_row=1)
        ch_scaled = scale_text_to_fit(col_header, GAME_WIDTH - 16, preferred_scale=2.0)
        ch_rect = ch_scaled.get_rect(center=(GAME_WIDTH // 2, 170))
        screen.blit(ch_scaled, ch_rect)

        for i, entry in enumerate(self.scores[:MAX_SCORES]):
            name = entry["name"].ljust(3)
            score_str = str(entry["score"]).rjust(8)
            line = f"{name}      {score_str}"
            text = self.font.render_text(line, color_row=0)
            t_scaled = scale_text_to_fit(text, GAME_WIDTH - 16, preferred_scale=2.0)
            t_rect = t_scaled.get_rect(center=(GAME_WIDTH // 2, 200 + i * 24))
            screen.blit(t_scaled, t_rect)
