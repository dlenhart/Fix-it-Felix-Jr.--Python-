import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame  # noqa: E402
import pytest  # noqa: E402

from camera import Camera  # noqa: E402
from entities.building import Building  # noqa: E402
from sprite_sheet import SpriteSheet  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def display():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def test_glass_rect_plain_cell_and_door():
    building = Building(1, random.Random(0))
    plain = building.floors[0].cells[0]  # x=40, piece 16 is 24x48 on bottom_y 320
    assert building.glass_rect(plain) == pygame.Rect(46, 272 + 12, 12, 23)
    door = building.floors[0].cells[2]  # x=96, piece 2 is 48x64
    assert building.glass_rect(door) == pygame.Rect(96, 256, 48, 64)


def test_draw_leaves_pixels_near_bottom():
    building = Building(1, random.Random(0))
    screen = pygame.Surface((240, 320))
    screen.fill((0, 0, 0))
    building.draw(screen, SpriteSheet(), Camera(), 0)
    has_drawn_pixel = any(
        screen.get_at((x, y))[:3] != (0, 0, 0)
        for x in range(240)
        for y in range(256, 320)
    )
    assert has_drawn_pixel
