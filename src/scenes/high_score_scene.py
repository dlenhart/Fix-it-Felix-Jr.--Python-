import pygame

from audio.sound_manager import SoundManager
from constants.display import BLACK, GAME_WIDTH
from constants.high_scores import (
    CURRENT_LETTER_FLASH_COLOR_ROW, CURRENT_LETTER_FLASH_PERIOD_MASK,
    CURRENT_LETTER_FLASH_START_TICK, FIRST_LETTER_INDEX, HS_DISPLAY_TIMER_TICKS,
    INITIALS_COLOR_ROW, INITIALS_LENGTH, LETTER_OPTIONS, MAX_SCORES,
)
from controls.action import Action
from core.scene import Scene
from graphics.font_renderer import FontRenderer
from graphics.sprite_sheet import SpriteSheet
from graphics.text_layout import draw_centered_text, scale_to_screen_width
from paths import SCORES_FILE
from storage.score_repository import ScoreRepository


class HighScoreScene(Scene):
    def __init__(self, manager, final_score=0, score_repository: ScoreRepository | None = None):
        super().__init__(manager)
        self.final_score = final_score
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._score_repository = score_repository or ScoreRepository(SCORES_FILE)
        self.scores = self._score_repository.load()

        self._is_entering = self._qualifies()
        self._initials = ["A", "A", "A"]
        self._cursor = 0
        self._letter_index = FIRST_LETTER_INDEX
        self._display_ticks = 0
        self._flash_ticks = 0

    @property
    def initials(self):
        """The three entry letters as currently shown, as a snapshot."""
        return tuple(self._initials)

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
        self._score_repository.save(self.scores)

    def draw(self, screen, alpha=1.0):
        screen.fill(BLACK)

        draw_centered_text(screen, self.font, "HIGH SCORES", (GAME_WIDTH // 2, 40),
                           preferred_scale=3.0)

        if self._is_entering:
            draw_centered_text(screen, self.font, "ENTER YOUR INITIALS", (GAME_WIDTH // 2, 90),
                               color_row=1, preferred_scale=2.0)
            initials = scale_to_screen_width(self._render_initials(), preferred_scale=3.0)
            screen.blit(initials, initials.get_rect(center=(GAME_WIDTH // 2, 130)))

        draw_centered_text(screen, self.font, "NAME      SCORE", (GAME_WIDTH // 2, 170),
                           color_row=1, preferred_scale=2.0)

        for i, entry in enumerate(self.scores[:MAX_SCORES]):
            name = entry["name"].ljust(3)
            score_str = str(entry["score"]).rjust(8)
            draw_centered_text(screen, self.font, f"{name}      {score_str}",
                               (GAME_WIDTH // 2, 200 + i * 24), preferred_scale=2.0)
