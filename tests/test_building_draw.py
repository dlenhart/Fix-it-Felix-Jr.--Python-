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
from entities.felix import Felix  # noqa: E402
from entities.nicelander import Nicelander  # noqa: E402
from entities.pie import Pie  # noqa: E402
from sprite_sheet import SpriteSheet  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def display():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def test_glass_rect_plain_cell_and_door():
    building = Building(1, random.Random(0))
    plain = building.floors[0].cells[0]  # x=40, piece 16 is 24x48 at the ground floor's top, y 264
    assert building.glass_rect(plain) == pygame.Rect(46, 264 + 12, 12, 23)
    door = building.floors[0].cells[2]  # x=96, piece 2 is 48x64
    assert building.glass_rect(door) == pygame.Rect(96, 256, 48, 64)
    arched = building.floors[1].cells[2]  # FUN_00405550: the second floor's top row + 1, y 0xd8
    assert building.glass_rect(arched) == pygame.Rect(96, 0xD8, 48, 40)


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


def drawn_bounds(draw):
    """Bounding rect of what draw(screen) paints on a transparent screen."""
    screen = pygame.Surface((240, 320), pygame.SRCALPHA)
    screen.fill((0, 0, 0, 0))
    draw(screen)
    return screen.get_bounding_rect()


def test_felix_lowest_pixel_row_is_the_sill():
    building = Building(3, random.Random(0))
    for local_row, column in ((0, 0), (0, 2), (1, 2), (2, 2), (3, 4)):
        felix = Felix()
        felix.place_at(local_row, column, building)
        bounds = drawn_bounds(lambda screen: felix.draw(screen, SpriteSheet(), Camera(), 0))
        assert bounds.bottom - 1 == building.sill_y(building.cell(local_row, column))


def test_pie_sits_on_the_nicelander_node_centered_on_the_cell():
    building = Building(3, random.Random(0))
    for local_row, column in ((1, 0), (2, 2), (3, 4)):
        cell = building.cell(local_row, column)
        pie = Pie(cell)
        bounds = drawn_bounds(
            lambda screen: pie.draw(screen, SpriteSheet(), building, Camera(), 0))
        assert bounds.bottom - 1 == building.sill_y(cell) - 2
        assert bounds.left + bounds.width // 2 == building.sill_middle_x(cell)


def test_nicelander_bottom_row_is_two_pixels_above_the_sill():
    building = Building(3, random.Random(0))
    for local_row, column in ((1, 0), (2, 3), (3, 4)):
        cell = building.cell(local_row, column)
        node_x, node_y = building.nicelander_node(cell)
        assert (node_x, node_y) == (building.sill_middle_x(cell), building.sill_y(cell) - 2)
        nicelander = Nicelander(cell, 0)
        bounds = drawn_bounds(
            lambda screen: nicelander.draw(screen, SpriteSheet(), building, Camera(), 0))
        assert bounds.bottom - 1 == node_y


class RecordingScreen(pygame.Surface):
    """A 240x320 screen that logs where each blit lands."""

    def __init__(self):
        super().__init__((240, 320))
        self.blit_positions = []

    def blit(self, source, destination, area=None, *args):
        self.blit_positions.append((destination, area))
        return super().blit(source, destination, area, *args)


def test_street_tiles_piece_one_on_the_exe_runs():
    # FUN_00406050: piece 1 (16x16, 2 tiles) at x = cam x + (i - 0x1c) * 8 and cam x + (i + 0x1a) * 8
    # for i = 0, 2, ..., 0x1e, at y = cam y + 0x130.
    camera = Camera()
    camera.cut_to(-160, 0)
    screen = RecordingScreen()
    Building(1, random.Random(0)).draw_street(screen, SpriteSheet(), camera, 0)
    expected_xs = {-160 + (i + offset) * 8 for i in range(0, 0x1F, 2) for offset in (-0x1C, 0x1A)}
    assert {destination for destination, _ in screen.blit_positions} == {(x, 0x130) for x in expected_xs}
    assert len(screen.blit_positions) == 32
    assert all(area == pygame.Rect(0, 0, 16, 16) for _, area in screen.blit_positions)


def test_street_is_skipped_once_scrolled_below_the_screen():
    camera = Camera()
    camera.cut_to(0, 0x10)  # y 0x130 + 0x10 = 0x140, the exe's cut-off
    screen = RecordingScreen()
    Building(1, random.Random(0)).draw_street(screen, SpriteSheet(), camera, 0)
    assert screen.blit_positions == []
