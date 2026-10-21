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
# Ghidra-confirmed: 38 characters including space, A-Z, 0-9, period
LETTER_OPTIONS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."


def load_scores():
    if os.path.exists(SCORES_FILE):
        try:
            with open(SCORES_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
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
        self._letter_index = 0
        self._display_ticks = 0

    def _qualifies(self):
        if self.final_score <= 0:
            return False
        if len(self.scores) < MAX_SCORES:
            return True
        return self.final_score > self.scores[-1]["score"]

    def on_enter(self):
        self.sound.play_music("high_score", loop=False)

    def on_exit(self):
        self.sound.stop_music()

    def tick(self, input_handler):
        """One game tick (1/60s). All game logic is tick-counted."""
        if self._is_entering:
            if input_handler.is_just_pressed(Action.UP):
                self._letter_index = (self._letter_index - 1) % len(LETTER_OPTIONS)
                self._initials[self._cursor] = LETTER_OPTIONS[self._letter_index]
                self.sound.play_sfx("menu_select")
            elif input_handler.is_just_pressed(Action.DOWN):
                self._letter_index = (self._letter_index + 1) % len(LETTER_OPTIONS)
                self._initials[self._cursor] = LETTER_OPTIONS[self._letter_index]
                self.sound.play_sfx("menu_select")
            elif input_handler.is_just_pressed(Action.JUMP):
                self._cursor += 1
                self._letter_index = 0
                self.sound.play_sfx("menu_confirm")
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

            initials_str = " ".join(self._initials)
            initials = self.font.render_text(initials_str, color_row=0)
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
