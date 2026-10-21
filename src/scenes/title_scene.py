import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK, TITLE_BLINK_TICKS
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer


class TitleScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._blink_ticks = 0
        self._show_press_start = True

    def on_enter(self):
        self.sound.play_music("title")

    def on_exit(self):
        self.sound.stop_music()

    def tick(self, input_handler):
        """One game tick (1/60s). All game logic is tick-counted."""
        if (input_handler.is_just_pressed(Action.START) or
                input_handler.is_just_pressed(Action.JUMP)):
            self.sound.play_sfx("menu_confirm")
            from scenes.cutscene_scene import CutsceneScene
            self.manager.replace(CutsceneScene(self.manager))
            return

        self._blink_ticks += 1
        if self._blink_ticks >= TITLE_BLINK_TICKS:
            self._blink_ticks = 0
            self._show_press_start = not self._show_press_start

    def draw(self, screen, alpha=1.0):
        screen.fill(BLACK)

        # All coordinates in 240x320 internal space — no scaling needed
        try:
            logo = self.sprites.get_sprite("title_logo", 0, 0)
            rect = logo.get_rect(center=(GAME_WIDTH // 2, 80))
            screen.blit(logo, rect)
        except (KeyError, IndexError):
            title = self.font.render_text("FIX-IT FELIX JR", color_row=0)
            rect = title.get_rect(center=(GAME_WIDTH // 2, 80))
            screen.blit(title, rect)

        copyright_text = self.font.render_text("@TOBIKOMI COMPANY 1982", color_row=1)
        rect = copyright_text.get_rect(center=(GAME_WIDTH // 2, 130))
        screen.blit(copyright_text, rect)

        if self._show_press_start:
            start_text = self.font.render_text("PRESS START", color_row=0)
            rect = start_text.get_rect(center=(GAME_WIDTH // 2, 250))
            screen.blit(start_text, rect)
