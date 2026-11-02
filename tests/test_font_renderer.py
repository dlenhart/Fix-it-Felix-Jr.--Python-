import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from font_renderer import FontRenderer, scale_text_to_fit  # noqa: E402
from sprite_data import FONT_GLYPH_SIZE  # noqa: E402
from sprite_sheet import SpriteSheet  # noqa: E402

SUPPORTED_CHARS = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"
renderer = FontRenderer(SpriteSheet())


def pixels_of(surface):
    return pygame.image.tostring(surface, "RGBA")


def has_visible_pixel(surface):
    width, height = surface.get_size()
    return any(surface.get_at((x, y)).a > 0 for x in range(width) for y in range(height))


def test_digit_one_renders_one_not_slash():
    assert pixels_of(renderer.render_text("1")) != pixels_of(renderer.render_text("/"))


def test_every_supported_char_renders_nonempty():
    for char in SUPPORTED_CHARS:
        surface = renderer.render_text(char)
        assert surface.get_size() == (FONT_GLYPH_SIZE, FONT_GLYPH_SIZE)
        assert has_visible_pixel(surface), f"{char!r} rendered blank"


def test_render_text_uppercases_and_sizes_by_length():
    surface = renderer.render_text("abc")
    assert surface.get_width() == 3 * FONT_GLYPH_SIZE
    assert pixels_of(surface) == pixels_of(renderer.render_text("ABC"))


def test_unsupported_char_leaves_a_blank_cell():
    assert not has_visible_pixel(renderer.render_text("~"))


def test_opaque_glyph_cell_has_no_transparent_pixel_and_is_cached():
    cell = renderer.render_opaque_glyph_cell("A", 6)
    assert all(cell.get_at((x, y)).a == 255
               for x in range(FONT_GLYPH_SIZE) for y in range(FONT_GLYPH_SIZE))
    assert renderer.render_opaque_glyph_cell("A", 6) is cell


def test_scale_text_to_fit_never_exceeds_max_width():
    surface = renderer.render_text("HEY. YOU MOVED MY STUMP!")
    scaled = scale_text_to_fit(surface, 240, 2.0)
    assert scaled.get_width() <= 240
    assert scaled.get_width() > surface.get_width()  # still scaled up, not collapsed


def test_scale_text_to_fit_keeps_preferred_scale_when_it_fits():
    surface = renderer.render_text("HI")
    scaled = scale_text_to_fit(surface, 240, 2.0)
    assert scaled.get_size() == (surface.get_width() * 2, surface.get_height() * 2)


def test_scale_text_to_fit_empty_text_stays_one_pixel_wide():
    scaled = scale_text_to_fit(renderer.render_text(""), 240, 2.0)
    assert scaled.get_width() == 1
