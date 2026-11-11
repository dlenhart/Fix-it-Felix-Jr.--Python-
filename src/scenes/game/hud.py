"""The in-game HUD band: score, level and lives (layout [ASSUMED], spec section 10)."""

import pygame

from constants.display import BLACK, GAME_WIDTH
from constants.hud import (
    HUD_BAND_HEIGHT, HUD_LEVEL_POSITION, HUD_LIFE_COUNT_GAP, HUD_LIFE_ICON_SPACING,
    HUD_LIFE_ICON_Y, HUD_LIFE_ICONS_RIGHT_X, HUD_MAX_LIFE_ICONS, HUD_SCORE_POSITION,
)
from exe_data.sprite_data import LIFE_ICON_PIECE
from graphics.font_renderer import FontRenderer
from graphics.sprite_sheet import SpriteSheet


class Hud:
    """Draws the HUD band over the top of the playfield."""

    def __init__(self, font: FontRenderer, sprites: SpriteSheet):
        self._font = font
        self._sprites = sprites

    def draw(self, screen: pygame.Surface, score: int, level: int, lives: int,
             palette: int) -> None:
        screen.fill(BLACK, pygame.Rect(0, 0, GAME_WIDTH, HUD_BAND_HEIGHT))

        score_text = self._font.render_text(f"{score:06d}", color_row=0)
        screen.blit(score_text, HUD_SCORE_POSITION)

        level_text = self._font.render_text(f"LEVEL {level}", color_row=0)
        screen.blit(level_text, HUD_LEVEL_POSITION)

        self._draw_life_icons(screen, lives, palette)

    def _draw_life_icons(self, screen: pygame.Surface, lives: int, palette: int) -> None:
        icon = self._sprites.get_piece(LIFE_ICON_PIECE, palette)
        icon_count = min(lives, HUD_MAX_LIFE_ICONS)
        left_x = HUD_LIFE_ICONS_RIGHT_X
        for _ in range(icon_count):
            left_x -= icon.get_width()
            screen.blit(icon, (left_x, HUD_LIFE_ICON_Y))
            left_x -= HUD_LIFE_ICON_SPACING

        if lives <= HUD_MAX_LIFE_ICONS:
            return
        count_text = self._font.render_text(f"X{lives}", color_row=0)
        text_y = HUD_LIFE_ICON_Y + (icon.get_height() - count_text.get_height()) // 2
        text_x = left_x - HUD_LIFE_COUNT_GAP - count_text.get_width()
        screen.blit(count_text, (text_x, text_y))
