import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from constants.display import GAME_HEIGHT, GAME_WIDTH  # noqa: E402
from constants.hud import HUD_BAND_HEIGHT, HUD_LIFE_ICONS_RIGHT_X  # noqa: E402
from graphics.font_renderer import FontRenderer  # noqa: E402
from graphics.sprite_sheet import SpriteSheet  # noqa: E402
from scenes.game.hud import Hud  # noqa: E402


def draw_hud(lives):
    sprites = SpriteSheet()
    screen = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
    screen.fill((255, 0, 255))
    Hud(FontRenderer(sprites), sprites).draw(screen, score=1200, level=3, lives=lives, palette=0)
    return screen


def leftmost_drawn_x_in_band(screen):
    for x in range(GAME_WIDTH // 2, HUD_LIFE_ICONS_RIGHT_X):
        if any(screen.get_at((x, y))[:3] != (0, 0, 0) for y in range(HUD_BAND_HEIGHT)):
            return x
    return None


def test_the_band_is_cleared_and_nothing_spills_below_it():
    screen = draw_hud(lives=3)
    assert screen.get_at((GAME_WIDTH // 2, HUD_BAND_HEIGHT - 1))[:3] == (0, 0, 0)
    assert screen.get_at((GAME_WIDTH // 2, HUD_BAND_HEIGHT))[:3] == (255, 0, 255)


def test_more_than_five_lives_adds_a_count_left_of_the_icons():
    five = leftmost_drawn_x_in_band(draw_hud(lives=5))
    twelve = leftmost_drawn_x_in_band(draw_hud(lives=12))
    assert twelve < five
