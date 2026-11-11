from audio.sound_manager import SoundManager
from constants.display import BLACK, GAME_WIDTH
from constants.screens import TITLE_BLINK_TICKS
from controls.action import Action
from core.scene import Scene
from graphics.font_renderer import FontRenderer
from graphics.sprite_sheet import SpriteSheet
from graphics.text_layout import draw_centered_text


class TitleScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._blink_ticks = 0
        self._show_press_start = True

    def on_enter(self):
        # [USER] loops; the exe plays the title music once.
        self.sound.play_music("title", loop=True)

    def on_exit(self):
        self.sound.stop_music()

    def tick(self, input_handler):
        """One game tick (1/60s). All game logic is tick-counted."""
        if (input_handler.is_just_pressed(Action.START) or
                input_handler.is_just_pressed(Action.JUMP)):
            self.sound.play_sfx("new_game")  # FUN_004076e0
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
            # TODO: fail-fast says let a missing logo raise instead of falling back to text.
            draw_centered_text(screen, self.font, "FIX-IT FELIX JR", (GAME_WIDTH // 2, 80))

        draw_centered_text(screen, self.font, "@TOBIKOMI COMPANY 1982", (GAME_WIDTH // 2, 130),
                           color_row=1)

        if self._show_press_start:
            draw_centered_text(screen, self.font, "PRESS START", (GAME_WIDTH // 2, 250))
