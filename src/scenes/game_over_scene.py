from constants.display import BLACK, GAME_HEIGHT, GAME_WIDTH
from constants.screens import GAME_OVER_TICKS
from core.scene import Scene
from graphics.font_renderer import FontRenderer
from graphics.sprite_sheet import SpriteSheet
from graphics.text_layout import draw_centered_text


class GameOverScene(Scene):
    def __init__(self, manager, final_score):
        super().__init__(manager)
        self.final_score = final_score
        self.sprites = SpriteSheet()
        self.font = FontRenderer(self.sprites)
        self._ticks = 0

    def tick(self, input_handler):
        """One game tick (1/60s). All game logic is tick-counted."""
        self._ticks += 1
        if self._ticks >= GAME_OVER_TICKS:
            from scenes.high_score_scene import HighScoreScene
            self.manager.replace(HighScoreScene(self.manager, self.final_score))

    def draw(self, screen, alpha=1.0):
        screen.fill(BLACK)
        draw_centered_text(screen, self.font, "GAME OVER", (GAME_WIDTH // 2, GAME_HEIGHT // 2 - 30),
                           preferred_scale=4.0)
        draw_centered_text(screen, self.font, f"SCORE {self.final_score:06d}",
                           (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 40), color_row=1,
                           preferred_scale=2.0)
