import pygame

from exe_data.sprite_data import (
    FIRST_GLYPH_CODE, FONT_GLYPH_CHARACTERS, FONT_GLYPH_SIZE, FONT_ROWS, LAST_GLYPH_CODE,
    font_row_for_exe_colour,
)


class FontRenderer:
    """Renders text from the atlas font, one colour per font row."""

    def __init__(self, sprite_sheet, palette=0):
        self._sprite_sheet = sprite_sheet
        self._palette = palette
        self._char_cache = {}
        self._build_char_map()

    def _build_char_map(self):
        for row_idx, row_info in FONT_ROWS.items():
            y = row_info["y"]
            cw = row_info["char_width"]
            ch = row_info["char_height"]
            start_x = row_info["start_x"]
            for i, char in enumerate(FONT_GLYPH_CHARACTERS):
                x = start_x + i * cw
                self._char_cache[(char, row_idx)] = self._sprite_sheet.get_region(
                    (x, y, cw, ch), self._palette)

    def render_text(self, text, color_row=0):
        """Render text in one font row; lowercase draws as uppercase and space as a blank cell.

        Raises ValueError for a colour row the font lacks or a character it has no glyph for.
        """
        if color_row not in FONT_ROWS:
            raise ValueError(f"unknown font colour row: {color_row}")
        text = text.upper()
        row_info = FONT_ROWS[color_row]
        cw = row_info["char_width"]
        ch = row_info["char_height"]

        surface = pygame.Surface((len(text) * cw, ch), pygame.SRCALPHA)
        for i, char in enumerate(text):
            if char == " ":
                continue
            glyph = self._char_cache.get((char, color_row))
            if glyph is None:
                raise ValueError(f"no font glyph for {char!r} in {text!r}")
            surface.blit(glyph, (i * cw, 0))
        return surface

    def render_opaque_glyph_cell(self, char, exe_colour):
        """One 8x8 text-grid cell as FUN_0040f350 writes it: the glyph's atlas pixels, all opaque.

        FUN_0040f350 ORs 0xff000000 into every copied pixel, so the glyph's
        transparent background shows as whatever RGB the atlas stores there.
        """
        if not FIRST_GLYPH_CODE <= ord(char) <= LAST_GLYPH_CODE:
            raise ValueError(f"no font glyph for {char!r}")
        cache_key = ("opaque", char, exe_colour)
        if cache_key in self._char_cache:
            return self._char_cache[cache_key]
        row_info = FONT_ROWS[font_row_for_exe_colour(exe_colour)]
        glyph_x = (ord(char) - FIRST_GLYPH_CODE) * FONT_GLYPH_SIZE
        cell = self._sprite_sheet.get_region(
            (glyph_x, row_info["y"], FONT_GLYPH_SIZE, FONT_GLYPH_SIZE), self._palette).copy()
        for y in range(FONT_GLYPH_SIZE):
            for x in range(FONT_GLYPH_SIZE):
                red, green, blue, _ = cell.get_at((x, y))
                cell.set_at((x, y), (red, green, blue, 255))
        self._char_cache[cache_key] = cell
        return cell
