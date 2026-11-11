"""Sill obstacles: placement on the section's top floors and their world rect (FUN_00406e00)."""
import random

import pygame

from constants.hazards import HAZARD_FLOOR_COUNT, SILL_OBSTACLES_MAX_PER_FLOOR
from exe_data.sprite_data import SILL_OBSTACLE_FRAME_SIZE, SILL_OBSTACLE_ORIGIN
from world.building import Building
from world.floor import Floor
from world.level_types import CellKind
from world.window_cell import WindowCell


def sill_obstacle_rect(building: Building, cell: WindowCell) -> pygame.Rect:
    """World rect of a cell's sill obstacle frame, bounce included.

    The node is Building.sill_obstacle_node, and anim 91's origin (11, 5) is
    the slab art's bottom center, so on a pane window the art covers rows 31-36,
    resting on top of the ledge.
    """
    node_x, node_y = building.sill_obstacle_node(cell)
    origin_x, origin_y = SILL_OBSTACLE_ORIGIN
    return pygame.Rect(node_x - origin_x, node_y + cell.sill_obstacle_offset_y - origin_y,
                       *SILL_OBSTACLE_FRAME_SIZE)


def hazard_floors(building: Building) -> list[Floor]:
    """The section's top three floors; the bottom floor is hazard-free."""
    return building.section_floors()[-HAZARD_FLOOR_COUNT:]


def place_sill_obstacles(building: Building, count: int, rng: random.Random) -> None:
    """Set has_sill_obstacle on random non-arched cells of the section's top 3 floors.

    At most two per floor (FUN_00406e00). Raises ValueError if count cannot fit.
    """
    floors = hazard_floors(building)
    if count > SILL_OBSTACLES_MAX_PER_FLOOR * len(floors):
        raise ValueError(f"cannot place {count} sill obstacles")
    for _ in range(count):
        open_floors = [
            floor for floor in floors
            if sum(cell.has_sill_obstacle for cell in floor.cells) < SILL_OBSTACLES_MAX_PER_FLOOR
        ]
        floor = rng.choice(open_floors)
        open_cells = [cell for cell in floor.cells
                      if cell.kind != CellKind.ARCHED and not cell.has_sill_obstacle]
        rng.choice(open_cells).has_sill_obstacle = True


def clear_sill_obstacles(building: Building) -> None:
    """Remove every sill obstacle of the active section."""
    for floor in building.section_floors():
        for cell in floor.cells:
            cell.has_sill_obstacle = False
