"""Render a whole level's building to PNG for visual layout checks.

Usage: python3 tools/render_level.py --level N --out DIR
Writes level{N}_intact.png and level{N}_damaged.png (headless).
"""

import argparse
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame  # noqa: E402

from camera import Camera  # noqa: E402
from entities.building import Building  # noqa: E402
from level_config import FLOOR_PIECE, FloorType  # noqa: E402
from sprite_sheet import SpriteSheet  # noqa: E402

IMAGE_WIDTH = 240
MARGIN = 24
PALETTE = 0
DAMAGED_FLOOR_INDEX = 2  # first BRICK_SHORT floor
DOOR_DAMAGE_SHOWN = 3
# Top/bottom differ so each of states 0-5 shows up as a top and as a bottom pane.
PANE_STATE_PAIRS = ((0, 3), (1, 4), (2, 5), (3, 0), (4, 1))


def apply_damage_mix(building: Building) -> None:
    floor = building.floors[DAMAGED_FLOOR_INDEX]
    if floor.floor_type != FloorType.BRICK_SHORT:
        raise ValueError(f"floor {DAMAGED_FLOOR_INDEX} is {floor.floor_type.name}")
    for cell, (top, bottom) in zip(floor.cells, PANE_STATE_PAIRS, strict=True):
        cell.top_pane = top
        cell.bottom_pane = bottom
    building.floors[0].cells[2].door_damage = DOOR_DAMAGE_SHOWN


def render(building: Building, sprites: SpriteSheet, path: str) -> None:
    roof = building.floors[-1]
    # Roof art is taller than its row, so the topmost art is the roof's top.
    topmost_art_y = roof.bottom_y - sprites.get_piece(FLOOR_PIECE[FloorType.ROOF], PALETTE).get_height()
    bottom_y = building.floors[0].bottom_y
    camera = Camera()
    camera.scroll_y = MARGIN - topmost_art_y
    surface = pygame.Surface((IMAGE_WIDTH, bottom_y - topmost_art_y + 2 * MARGIN))
    surface.fill((0, 0, 0))
    building.draw(surface, sprites, camera, PALETTE)
    pygame.image.save(surface, path)
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    pygame.init()
    pygame.display.set_mode((1, 1))
    sprites = SpriteSheet()
    building = Building(args.level, random.Random(0))
    render(building, sprites, os.path.join(args.out, f"level{args.level}_intact.png"))
    apply_damage_mix(building)
    render(building, sprites, os.path.join(args.out, f"level{args.level}_damaged.png"))


if __name__ == "__main__":
    main()
