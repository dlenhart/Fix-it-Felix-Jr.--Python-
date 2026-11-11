"""Placing rendered text on the 240x320 game surface."""

import pygame

from constants.display import GAME_WIDTH, TEXT_SIDE_MARGIN
from core.camera import Camera
from exe_data.sprite_data import FONT_GLYPH_SIZE, font_row_for_exe_colour
from graphics.font_renderer import FontRenderer


def scale_text_to_fit(surface, max_width, preferred_scale=2.0):
    """Scale a render_text() surface up by preferred_scale, but never wider
    than max_width — a fixed scale factor on a long string can otherwise
    overflow the 240px internal canvas and get clipped on both edges."""
    width, height = surface.get_size()
    scale = preferred_scale if width == 0 else min(preferred_scale, max_width / width)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    return pygame.transform.scale(surface, (new_width, new_height))


def scale_to_screen_width(surface: pygame.Surface, preferred_scale: float) -> pygame.Surface:
    """Scale up by preferred_scale, capped to the screen width less the side margins."""
    return scale_text_to_fit(surface, GAME_WIDTH - 2 * TEXT_SIDE_MARGIN, preferred_scale)


def draw_centered_text(screen: pygame.Surface, font: FontRenderer, text: str,
                       center: tuple[int, int], color_row: int = 0,
                       preferred_scale: float | None = None) -> None:
    """Render text centered on a screen point, optionally scaled up to fit the screen width."""
    surface = font.render_text(text, color_row=color_row)
    if preferred_scale is not None:
        surface = scale_to_screen_width(surface, preferred_scale)
    screen.blit(surface, surface.get_rect(center=center))


def draw_exe_text(screen: pygame.Surface, font: FontRenderer, camera: Camera, text: str,
                  column: int, row: int, exe_colour: int, offset_x: int = 0) -> None:
    """Draw text the way FUN_0040f140 does: 8x8 glyphs from cell (column, row), camera-relative.

    Screen x = DAT_0041a298 + column * 8 (+ offset_x; FUN_0040f1d0 adds 4) and
    screen y = DAT_0041a248 + row * 8, so the text scrolls with the world.
    """
    surface = font.render_text(text, color_row=font_row_for_exe_colour(exe_colour))
    screen.blit(surface, (camera.to_screen_x(column * FONT_GLYPH_SIZE + offset_x),
                          camera.to_screen_y(row * FONT_GLYPH_SIZE)))
