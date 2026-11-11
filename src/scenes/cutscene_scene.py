import pygame

from audio.sound_manager import SoundManager
from constants.display import GAME_HEIGHT, GAME_WIDTH, SKY_BLUE
from constants.screens import CUTSCENE_STEPS
from controls.action import Action
from core.scene import Scene
from graphics.font_renderer import FontRenderer
from graphics.sprite_sheet import SpriteSheet
from graphics.text_layout import draw_centered_text


class CutsceneScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._step = 0
        self._ticks = 0

    def on_enter(self):
        self.sound.play_music("intro", loop=False)

    def on_exit(self):
        self.sound.stop_music()

    def tick(self, input_handler):
        """One game tick (1/60s). All game logic is tick-counted."""
        if (input_handler.is_just_pressed(Action.JUMP) or
                input_handler.is_just_pressed(Action.START)):
            self._start_game()
            return

        self._ticks += 1
        if self._step < len(CUTSCENE_STEPS):
            if self._ticks >= CUTSCENE_STEPS[self._step]["duration_ticks"]:
                self._ticks = 0
                self._step += 1
                if self._step >= len(CUTSCENE_STEPS):
                    self._start_game()

    def _start_game(self):
        from scenes.game.game_scene import GameScene
        self.manager.replace(GameScene(self.manager))

    def draw(self, screen, alpha=1.0):
        screen.fill(SKY_BLUE)

        if self._step >= len(CUTSCENE_STEPS):
            return

        step = CUTSCENE_STEPS[self._step]

        if step["sprite"]:
            try:
                sprite = self.sprites.get_sprite(step["sprite"], 0, 0)
                sprite_scaled = pygame.transform.scale(sprite,
                    (sprite.get_width() * 2, sprite.get_height() * 2))
                rect = sprite_scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 - 40))
                screen.blit(sprite_scaled, rect)
            except (KeyError, IndexError):
                # TODO: fail-fast says let a missing sprite raise instead of skipping it.
                pass

        if step["text"]:
            draw_centered_text(screen, self.font, step["text"],
                               (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 80), preferred_scale=2.0)
