import pygame
from sprite_data import FONT_GLYPH_SIZE, FONT_ROWS, font_row_for_exe_colour

# [EXE] FUN_0040f140 / FUN_0040f350 draw characters 0x20..0x5d; glyph x is
# (char - 0x20) * 8 from the font origin.
FIRST_GLYPH_CODE = 0x20


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

    def render_opaque_glyph_cell(self, char, exe_colour):
        """One 8x8 text-grid cell as FUN_0040f350 writes it: the glyph's atlas pixels, all opaque.

        FUN_0040f350 ORs 0xff000000 into every copied pixel, so the glyph's
        transparent background shows as whatever RGB the atlas stores there.
        """
        cache_key = ("opaque", char, exe_colour)
        if cache_key in self._char_cache:
            return self._char_cache[cache_key]
        row_info = FONT_ROWS[font_row_for_exe_colour(exe_colour)]
        glyph_x = (ord(char) - FIRST_GLYPH_CODE) * FONT_GLYPH_SIZE
        atlas = self._sprite_sheet._get_atlas(self._palette)
        cell = atlas.subsurface(
            pygame.Rect(glyph_x, row_info["y"], FONT_GLYPH_SIZE, FONT_GLYPH_SIZE)).copy()
        for y in range(FONT_GLYPH_SIZE):
            for x in range(FONT_GLYPH_SIZE):
                red, green, blue, _ = cell.get_at((x, y))
                cell.set_at((x, y), (red, green, blue, 255))
        self._char_cache[cache_key] = cell
        return cell


def scale_text_to_fit(surface, max_width, preferred_scale=2.0):
    """Scale a render_text() surface up by preferred_scale, but never wider
    than max_width — a fixed scale factor on a long string can otherwise
    overflow the 240px internal canvas and get clipped on both edges."""
    width, height = surface.get_size()
    scale = preferred_scale if width == 0 else min(preferred_scale, max_width / width)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    return pygame.transform.scale(surface, (new_width, new_height))
