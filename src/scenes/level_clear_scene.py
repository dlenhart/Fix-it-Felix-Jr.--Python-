import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer, scale_text_to_fit


class LevelClearScene(Scene):
    def __init__(self, manager, level, score):
        super().__init__(manager)
        self.level = level
        self.score = score
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._ticks = 0

    def on_enter(self):
        self.sound.play_music("level_clear", loop=False)

    def on_exit(self):
        self.sound.stop_music()

    def _medal_name(self):
        if self.level <= 3:
            return "medal_bronze"
        elif self.level <= 7:
            return "medal_silver"
        return "medal_gold"

    def _medal_label(self):
        if self.level <= 3:
            return "BRONZE"
        elif self.level <= 7:
            return "SILVER"
        return "GOLD"

    def tick(self, input_handler):
        """One game tick (250ms). All game logic is tick-counted."""
        if input_handler.is_just_pressed(Action.JUMP) and self._ticks >= 4:  # 1.0s x 4 ticks/sec
            self._advance_to_next_level()
            return

        self._ticks += 1
        if self._ticks >= 20:  # 5.0s x 4 ticks/sec
            self._advance_to_next_level()
            return

    def _advance_to_next_level(self):
        from scenes.game_scene import GameScene
        game = GameScene(self.manager)
        game.level = self.level + 1
        game.felix.score = self.score
        self.manager.replace(game)

    def draw(self, screen):
        screen.fill(BLACK)

        clear_text = self.font.render_text("LEVEL CLEAR!", color_row=0)
        scaled = scale_text_to_fit(clear_text, GAME_WIDTH - 16, preferred_scale=3.0)
        rect = scaled.get_rect(center=(GAME_WIDTH // 2, 100))
        screen.blit(scaled, rect)

        try:
            medal = self.sprites.get_sprite(self._medal_name(), 0, 0)
            medal_scaled = pygame.transform.scale(medal,
                (medal.get_width() * 2, medal.get_height() * 2))
            rect = medal_scaled.get_rect(center=(GAME_WIDTH // 2, 240))
            screen.blit(medal_scaled, rect)
        except (KeyError, IndexError):
            medal_label = self.font.render_text(self._medal_label() + " MEDAL", color_row=1)
            m_scaled = scale_text_to_fit(medal_label, GAME_WIDTH - 16, preferred_scale=2.0)
            rect = m_scaled.get_rect(center=(GAME_WIDTH // 2, 240))
            screen.blit(m_scaled, rect)

        score_text = self.font.render_text(f"SCORE {self.score:06d}", color_row=1)
        s_scaled = scale_text_to_fit(score_text, GAME_WIDTH - 16, preferred_scale=2.0)
        rect = s_scaled.get_rect(center=(GAME_WIDTH // 2, 350))
        screen.blit(s_scaled, rect)
