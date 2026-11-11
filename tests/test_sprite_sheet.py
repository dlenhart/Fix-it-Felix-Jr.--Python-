import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402
import pytest  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from exe_data import level_table  # noqa: E402
from exe_data import sprite_data  # noqa: E402
from exe_data.exe_tables import BUILDING_PIECES, SPRITE_FRAMES  # noqa: E402
from graphics.hammer_sheet import HammerSheet  # noqa: E402
from graphics.sprite_sheet import SpriteSheet  # noqa: E402



@pytest.fixture(autouse=True)
def display_ready():
    # Other test modules may quit pygame; convert_alpha needs a live display.
    pygame.init()
    pygame.display.set_mode((1, 1))


@pytest.fixture
def sheet():
    return SpriteSheet()


def test_get_frame_unknown_id_raises(sheet):
    with pytest.raises(IndexError):
        sheet.get_frame(len(SPRITE_FRAMES))
    with pytest.raises(IndexError):
        sheet.get_frame(-1)


def test_get_piece_unknown_id_raises(sheet):
    with pytest.raises(IndexError):
        sheet.get_piece(len(BUILDING_PIECES))
    with pytest.raises(IndexError):
        sheet.get_piece(-1)


def test_get_sprite_unknown_name_or_frame_raises(sheet):
    with pytest.raises(KeyError):
        sheet.get_sprite("no_such_sprite")
    name = next(iter(sprite_data.SPRITES))
    with pytest.raises(IndexError):
        sheet.get_sprite(name, frame=len(sprite_data.SPRITES[name]))


def test_get_sprite_returns_region_of_listed_size_and_is_cached(sheet):
    name = next(iter(sprite_data.SPRITES))
    _, _, width, height = sprite_data.SPRITES[name][0]
    sprite = sheet.get_sprite(name)
    assert sprite.get_size() == (width, height)
    assert sheet.get_sprite(name) is sprite
    assert sheet.get_frame_count(name) == len(sprite_data.SPRITES[name])
    assert sheet.get_frame_count("no_such_sprite") == 0


def test_flipped_frame_is_mirror_of_unflipped(sheet):
    frame = sheet.get_frame(34)
    flipped = sheet.get_frame(34, is_flipped=True)
    assert flipped.get_size() == frame.get_size()
    width, height = frame.get_size()
    assert any(frame.get_at((x, y)) != flipped.get_at((x, y))
               for x in range(width) for y in range(height))  # not a vacuous symmetric frame
    for y in range(height):
        for x in range(width):
            assert flipped.get_at((x, y)) == frame.get_at((width - 1 - x, y))


def test_frame_and_piece_have_exe_table_size_and_are_cached(sheet):
    _, _, width, height = SPRITE_FRAMES[5]
    assert sheet.get_frame(5).get_size() == (width, height)
    assert sheet.get_frame(5) is sheet.get_frame(5)
    _, _, piece_width, piece_height = BUILDING_PIECES[3]
    assert sheet.get_piece(3).get_size() == (piece_width, piece_height)
    assert sheet.get_piece(3) is sheet.get_piece(3)


def _named_ids(suffix):
    for name, value in vars(sprite_data).items():
        if not name.endswith(suffix):
            continue
        ids = value if isinstance(value, tuple) else (value,)
        yield name, [frame_id for frame_id in ids if isinstance(frame_id, int)]


def test_every_named_frame_id_in_sprite_data_resolves(sheet):
    resolved = 0
    for suffix in ("_FRAMES", "_FRAME", "_FRAMES_RIGHT", "_FRAMES_LEFT", "_FRAME_INTACT"):
        for name, frame_ids in _named_ids(suffix):
            for frame_id in frame_ids:
                sheet.get_frame(frame_id)
                resolved += 1
    assert resolved > 20
    for character in range(sprite_data.NICELANDER_CHARACTER_COUNT):
        for frame_id in sprite_data.nicelander_rise_frame_ids(character):
            sheet.get_frame(frame_id)


def test_every_named_piece_id_resolves(sheet):
    sheet.get_piece(sprite_data.LIFE_ICON_PIECE)
    for piece_id in (*level_table.FLOOR_PIECE.values(), *level_table.CELL_PIECE.values()):
        sheet.get_piece(piece_id)


def test_hammer_sheet_sprite_size_and_unknown_name():
    hammers = HammerSheet()
    _, _, width, height = sprite_data.HAMMER_SPRITES["hammer_swing"][0]
    sprite = hammers.get_sprite("hammer_swing")
    assert sprite.get_size() == (width, height)
    assert hammers.get_sprite("hammer_swing") is sprite
    with pytest.raises(KeyError):
        hammers.get_sprite("no_such_hammer")


def test_get_region_slices_the_atlas_and_caches_it():
    sheet = SpriteSheet()
    region = sheet.get_region((8, 968, 8, 8))
    assert region.get_size() == (8, 8)
    assert sheet.get_region((8, 968, 8, 8)) is region


def test_get_region_outside_the_atlas_raises():
    with pytest.raises(ValueError):
        SpriteSheet().get_region((1020, 1020, 8, 8))


def test_frames_and_pieces_with_the_same_id_do_not_share_a_cache_entry():
    sheet = SpriteSheet()
    assert sheet.get_frame(5) is not sheet.get_piece(5)
    assert sheet.get_frame(5).get_size() == SPRITE_FRAMES[5][2:]
    assert sheet.get_piece(5).get_size() == BUILDING_PIECES[5][2:]
