import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from constants.display import GAME_HEIGHT, GAME_WIDTH, TEXT_SIDE_MARGIN  # noqa: E402
from graphics.font_renderer import FontRenderer  # noqa: E402
from graphics.sprite_sheet import SpriteSheet  # noqa: E402
from graphics.text_layout import draw_centered_text, scale_to_screen_width  # noqa: E402

font = FontRenderer(SpriteSheet())


def drawn_bounds(text, center, **kwargs):
    screen = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
    draw_centered_text(screen, font, text, center, **kwargs)
    return screen.get_bounding_rect()


def test_text_is_centered_on_the_point():
    bounds = drawn_bounds("HI", (100, 60))
    assert abs(bounds.centerx - 100) <= 1 and abs(bounds.centery - 60) <= 1


def test_preferred_scale_is_capped_to_the_screen_width_less_margins():
    long_text = font.render_text("HEY. YOU MOVED MY STUMP!")
    scaled = scale_to_screen_width(long_text, preferred_scale=4.0)
    assert scaled.get_width() <= GAME_WIDTH - 2 * TEXT_SIDE_MARGIN


def test_no_preferred_scale_draws_at_glyph_size():
    unscaled = drawn_bounds("PRESS START", (120, 160))
    scaled = drawn_bounds("PRESS START", (120, 160), preferred_scale=2.0)
    assert scaled.height > unscaled.height
