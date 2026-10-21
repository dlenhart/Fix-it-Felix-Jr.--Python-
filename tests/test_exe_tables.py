import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame
import pytest

from exe_tables import BUILDING_PIECES, SPRITE_FRAMES
from sprite_sheet import SpriteSheet


@pytest.fixture
def sprite_sheet():
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    return SpriteSheet()


def test_table_sizes():
    assert len(SPRITE_FRAMES) == 216
    assert len(BUILDING_PIECES) == 27


def test_pane_frames_span_glass_to_black():
    assert SPRITE_FRAMES[163] == (304, 0, 16, 16)
    assert SPRITE_FRAMES[168] == (320, 0, 16, 16)


def test_floor_pieces_match_floor_heights():
    assert BUILDING_PIECES[10] == (0, 0, 224, 48)
    assert BUILDING_PIECES[11] == (0, 48, 224, 56)
    assert BUILDING_PIECES[12] == (0, 104, 224, 56)
    assert BUILDING_PIECES[13] == (0, 160, 224, 56)
    assert BUILDING_PIECES[9] == (288, 800, 224, 160)


def test_cell_pieces():
    assert BUILDING_PIECES[16] == (272, 0, 24, 48)
    assert BUILDING_PIECES[2] == (320, 48, 48, 64)
    assert BUILDING_PIECES[6] == (224, 48, 48, 40)


def test_get_frame_returns_table_size(sprite_sheet):
    assert sprite_sheet.get_frame(163).get_size() == (16, 16)


def test_get_frame_flipped_is_mirrored_and_cached_separately(sprite_sheet):
    normal = sprite_sheet.get_frame(163)
    flipped = sprite_sheet.get_frame(163, is_flipped=True)
    assert flipped is not normal
    assert sprite_sheet.get_frame(163, is_flipped=True) is flipped
    assert sprite_sheet.get_frame(163) is normal
    width, height = normal.get_size()
    for x, y in ((0, 0), (3, 5), (width - 1, height - 1)):
        assert flipped.get_at((width - 1 - x, y)) == normal.get_at((x, y))


def test_get_piece_returns_table_size(sprite_sheet):
    assert sprite_sheet.get_piece(10).get_size() == (224, 48)


def test_get_frame_unknown_id_raises(sprite_sheet):
    with pytest.raises(IndexError):
        sprite_sheet.get_frame(216)
    with pytest.raises(IndexError):
        sprite_sheet.get_frame(-1)


def test_get_piece_unknown_id_raises(sprite_sheet):
    with pytest.raises(IndexError):
        sprite_sheet.get_piece(27)
