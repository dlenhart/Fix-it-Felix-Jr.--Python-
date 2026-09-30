import pygame
from sprite_data import FONT_ROWS


class FontRenderer:
    def __init__(self, sprite_sheet, palette=0):
        self._sprite_sheet = sprite_sheet
        self._palette = palette
        self._char_cache = {}
        self._build_char_map()

    def _build_char_map(self):
        ascii_chars = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for row_idx, row_info in FONT_ROWS.items():
            atlas = self._sprite_sheet._get_atlas(self._palette)
            y = row_info["y"]
            cw = row_info["char_width"]
            ch = row_info["char_height"]
            start_x = row_info["start_x"]
            for i, char in enumerate(ascii_chars):
                x = start_x + i * cw
                try:
                    surface = atlas.subsurface(pygame.Rect(x, y, cw, ch)).copy()
                    self._char_cache[(char, row_idx)] = surface
                except ValueError:
                    pass

    def render_text(self, text, color_row=0):
        text = text.upper()
        row_info = FONT_ROWS.get(color_row, FONT_ROWS[0])
        cw = row_info["char_width"]
        ch = row_info["char_height"]

        surface = pygame.Surface((len(text) * cw, ch), pygame.SRCALPHA)
        for i, char in enumerate(text):
            glyph = self._char_cache.get((char, color_row))
            if glyph:
                surface.blit(glyph, (i * cw, 0))
        return surface


def scale_text_to_fit(surface, max_width, preferred_scale=2.0):
    """Scale a render_text() surface up by preferred_scale, but never wider
    than max_width — a fixed scale factor on a long string can otherwise
    overflow the 240px internal canvas and get clipped on both edges."""
    width, height = surface.get_size()
    scale = preferred_scale if width == 0 else min(preferred_scale, max_width / width)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    return pygame.transform.scale(surface, (new_width, new_height))
