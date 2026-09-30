import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer, scale_text_to_fit


class GameOverScene(Scene):
    def __init__(self, manager, final_score):
        super().__init__(manager)
        self.final_score = final_score
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._ticks = 0

    def on_enter(self):
        self.sound.play_sfx("game_over")

    def tick(self, input_handler):
        """One game tick (250ms). All game logic is tick-counted."""
        self._ticks += 1
        if self._ticks >= 12:  # 3.0 real seconds x 4 ticks/sec
            from scenes.high_score_scene import HighScoreScene
            self.manager.replace(HighScoreScene(self.manager, self.final_score))

    def draw(self, screen, alpha=1.0):
        screen.fill(BLACK)

        game_over = self.font.render_text("GAME OVER", color_row=0)
        scaled = scale_text_to_fit(game_over, GAME_WIDTH - 16, preferred_scale=4.0)
        rect = scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 - 30))
        screen.blit(scaled, rect)

        score = self.font.render_text(f"SCORE {self.final_score:06d}", color_row=1)
        scaled_score = scale_text_to_fit(score, GAME_WIDTH - 16, preferred_scale=2.0)
        rect = scaled_score.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 + 40))
        screen.blit(scaled_score, rect)
