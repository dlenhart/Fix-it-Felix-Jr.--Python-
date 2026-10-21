"""Building model: floors stacked in world coordinates, each with window cells.

Also draws itself (floor art, cell pieces, window panes). Layout follows the exe's
FUN_00405e50 / FUN_00409610, damage FUN_00409840, fix and scoring FUN_00409a70.
"""

import random

import pygame

from camera import Camera
from exe_tables import BUILDING_PIECES
from level_config import (
    CELL_PIECE,
    CENTER_CELL_KIND,
    COLUMN_X,
    FACADE_X,
    FLOOR_HEIGHT,
    FLOOR_PIECE,
    FLOORS_PER_SECTION,
    STREET_Y,
    CellKind,
    FloorType,
    get_floor_sequence,
    get_level_config,
)
from sprite_data import PANE_FRAME_INTACT
from sprite_sheet import SpriteSheet

PANE_INTACT = 0
PANE_SMASHED = 5  # [EXE] FUN_00409840: pane state 5 is fully smashed

CENTER_COLUMN = 2
FIX_SCORE = 100  # [EXE] FUN_00409a70
FIX_LAST_WINDOW_SCORE = 500  # [EXE] FUN_00409a70 ("FIX LAST WINDOW 500 PTS")

DOOR_FIRST_PIECE = CELL_PIECE[CellKind.DOOR]
DOOR_MAX_DRAWN_DAMAGE = 3  # [ASSUMED] door art has 4 pieces: intact + 3 damage steps
PANE_TOP_OFFSET_Y = 0xC  # [EXE] FUN_00404ea0 top pane, from the cell piece top
PANE_BOTTOM_OFFSET_Y = 0x19  # [EXE] FUN_00404ea0 bottom pane
PANE_OFFSET_X = 4  # [ASSUMED] centers the pane art in the 24px cell piece
PANE_WINDOW_KINDS = (CellKind.PLAIN, CellKind.PEDIMENT_A, CellKind.PEDIMENT_B)
GLASS_OFFSET_X = 6  # [EXE] FUN_00404ea0 example rect
GLASS_WIDTH = 12  # [EXE] FUN_00404ea0 example rect
GLASS_HEIGHT = 23  # [EXE] FUN_00404ea0 example rect

# [ATLAS] rows between a cell piece's bottom and the bottom of its visible sill,
# measured in felix0.png. Pane pieces 14/15/16 (24x48) end their sill ledge
# (rows 37-42) above 5 transparent rows. The door (piece 2, steps) and the
# arched window (piece 6, balustrade) are opaque to their bottom row.
SILL_RISE_ABOVE_PIECE_BOTTOM: dict[CellKind, int] = {
    CellKind.PLAIN: 5,
    CellKind.PEDIMENT_A: 5,
    CellKind.PEDIMENT_B: 5,
    CellKind.DOOR: 0,
    CellKind.ARCHED: 0,
}


class WindowCell:
    """One window slot on a floor, with pane or door damage state."""

    def __init__(self, kind: CellKind, column: int, x: int, floor_index: int):
        self.kind = kind
        self.column = column
        self.x = x
        self.width: int = BUILDING_PIECES[CELL_PIECE[kind]][2]
        self.floor_index = floor_index
        self.top_pane = PANE_INTACT
        self.bottom_pane = PANE_INTACT
        self.door_damage = PANE_INTACT
        self.has_sill_obstacle = False

    @property
    def is_damageable(self) -> bool:
        # Decorative, never damaged. [ASSUMED] (spec section 3, first rebuild)
        return self.kind != CellKind.ARCHED

    @property
    def is_broken(self) -> bool:
        if self.kind == CellKind.DOOR:
            return self.door_damage > PANE_INTACT
        if self.kind == CellKind.ARCHED:
            return False
        return self.top_pane > PANE_INTACT or self.bottom_pane > PANE_INTACT

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    def damage(self, is_heavy: bool, rng: random.Random) -> None:
        """Apply FUN_00409840: set one random pane (or the door) to a damage level.

        Light sets rng.randint(1, 5), which can lower an already worse pane (exe
        behavior). Heavy sets 5. Arched cells ignore damage.
        """
        if not self.is_damageable:
            return
        level = PANE_SMASHED if is_heavy else rng.randint(1, 5)
        if self.kind == CellKind.DOOR:
            self.door_damage = level
        elif rng.random() < 0.5:
            self.top_pane = level
        else:
            self.bottom_pane = level

    def fix(self) -> None:
        """Restore the whole window; one hammer swing fixes every pane (FUN_00409a70)."""
        self.top_pane = PANE_INTACT
        self.bottom_pane = PANE_INTACT
        self.door_damage = PANE_INTACT


class Floor:
    """One floor of the building, stacked upward in world y."""

    def __init__(self, index: int, floor_type: FloorType, bottom_y: int):
        self.index = index
        self.floor_type = floor_type
        self.bottom_y = bottom_y
        self.height: int = FLOOR_HEIGHT[floor_type]
        self.cells: list[WindowCell] = self._build_cells()

    @property
    def top_y(self) -> int:
        return self.bottom_y - self.height

    def _build_cells(self) -> list[WindowCell]:
        if self.floor_type == FloorType.ROOF:
            return []
        center_kind = CENTER_CELL_KIND[self.floor_type]
        return [
            WindowCell(
                center_kind if column == CENTER_COLUMN else CellKind.PLAIN,
                column,
                x,
                self.index,
            )
            for column, x in enumerate(COLUMN_X[self.floor_type])
        ]


class Building:
    """All floors of a level plus the active section and window bookkeeping."""

    def __init__(self, level: int, rng: random.Random):
        self._rng = rng
        self.section_count = get_level_config(level).section_count
        self.section_index = 0
        self.floors = self._build_floors(level)

    @staticmethod
    def _build_floors(level: int) -> list[Floor]:
        floors: list[Floor] = []
        bottom_y = STREET_Y
        for index, floor_type in enumerate(get_floor_sequence(level)):
            floor = Floor(index, floor_type, bottom_y)
            floors.append(floor)
            bottom_y = floor.top_y
        return floors

    @staticmethod
    def _cell_piece_id(cell: WindowCell) -> int:
        if cell.kind == CellKind.DOOR:
            return DOOR_FIRST_PIECE + min(cell.door_damage, DOOR_MAX_DRAWN_DAMAGE)
        return CELL_PIECE[cell.kind]

    def _floor_for_cell(self, cell: WindowCell) -> Floor:
        return self.floors[cell.floor_index]

    def sill_y(self, cell: WindowCell) -> int:
        """World y where Felix's feet stand on the cell: the bottom of its visible sill.

        The exe keeps a per-cell sill y (cell+0x74); cell pieces are drawn
        bottom-aligned on the floor, so the sill sits a measured rise above it.
        """
        return self._floor_for_cell(cell).bottom_y - SILL_RISE_ABOVE_PIECE_BOTTOM[cell.kind]

    def glass_rect(self, cell: WindowCell) -> pygame.Rect:
        """World-space rect of the cell's breakable glass.

        Pane windows use the FUN_00404ea0 example rect; the door and arched
        window use their whole piece.
        """
        floor = self._floor_for_cell(cell)
        _, _, piece_width, piece_height = BUILDING_PIECES[CELL_PIECE[cell.kind]]
        piece_top = floor.bottom_y - piece_height
        if cell.kind not in PANE_WINDOW_KINDS:
            return pygame.Rect(cell.x, piece_top, piece_width, piece_height)
        return pygame.Rect(
            cell.x + GLASS_OFFSET_X,
            piece_top + PANE_TOP_OFFSET_Y,
            GLASS_WIDTH,
            GLASS_HEIGHT,
        )

    def draw(
        self,
        screen: pygame.Surface,
        sprites: SpriteSheet,
        camera: Camera,
        palette: int,
    ) -> None:
        """Draw floor art first (bottom-aligned), then cells and their panes."""
        screen_height = screen.get_height()
        for floor in self.floors:
            floor_surface = sprites.get_piece(FLOOR_PIECE[floor.floor_type], palette)
            # Roof art is taller than its row; it is bottom-aligned [ASSUMED].
            screen_bottom = camera.to_screen_y(floor.bottom_y)
            screen_top = screen_bottom - floor_surface.get_height()
            if screen_bottom <= 0 or screen_top >= screen_height:
                continue
            screen.blit(floor_surface, (FACADE_X, screen_top))
            for cell in floor.cells:
                self._draw_cell(screen, sprites, camera, palette, floor, cell)

    def _draw_cell(
        self,
        screen: pygame.Surface,
        sprites: SpriteSheet,
        camera: Camera,
        palette: int,
        floor: Floor,
        cell: WindowCell,
    ) -> None:
        piece = sprites.get_piece(self._cell_piece_id(cell), palette)
        piece_top = camera.to_screen_y(floor.bottom_y) - piece.get_height()
        screen.blit(piece, (cell.x, piece_top))
        if cell.kind not in PANE_WINDOW_KINDS:
            return
        pane_x = cell.x + PANE_OFFSET_X
        for offset_y, state in (
            (PANE_TOP_OFFSET_Y, cell.top_pane),
            (PANE_BOTTOM_OFFSET_Y, cell.bottom_pane),
        ):
            pane = sprites.get_frame(PANE_FRAME_INTACT + state, palette)
            screen.blit(pane, (pane_x, piece_top + offset_y))

    def section_floors(self, section_index: int | None = None) -> list[Floor]:
        """Return the floors of a section (default: the active one), bottom first."""
        if section_index is None:
            section_index = self.section_index
        start = section_index * FLOORS_PER_SECTION
        return self.floors[start:start + FLOORS_PER_SECTION]

    def cell(self, local_row: int, column: int) -> WindowCell:
        """Return a cell of the active section; local_row 0 is the bottom floor."""
        return self.section_floors()[local_row].cells[column]

    def floor_at_y(self, world_y: float) -> Floor | None:
        for floor in self.floors:
            if floor.top_y <= world_y < floor.bottom_y:
                return floor
        return None

    @property
    def broken_count(self) -> int:
        """Broken cells in the active section."""
        return sum(
            cell.is_broken
            for floor in self.section_floors()
            for cell in floor.cells
        )

    def damage(self, cell: WindowCell, is_heavy: bool) -> None:
        cell.damage(is_heavy, self._rng)

    def fix(self, cell: WindowCell) -> int:
        """Fix a cell and return the score: 0 if intact, 500 if last broken, else 100."""
        if not cell.is_broken:
            return 0
        cell.fix()
        return FIX_LAST_WINDOW_SCORE if self.broken_count == 0 else FIX_SCORE

    def is_section_clear(self) -> bool:
        return self.broken_count == 0

    @property
    def is_last_section(self) -> bool:
        return self.section_index == self.section_count - 1

    def advance_section(self) -> None:
        if self.is_last_section:
            raise RuntimeError("already on the last section")
        self.section_index += 1

    def ledge_y(self, section_index: int | None = None) -> int:
        """World y of the top of the section's top floor."""
        return self.section_floors(section_index)[-1].top_y

    def scroll_target(self, section_index: int) -> int:
        """Camera scroll that brings the section to the screen: heights of floors below it."""
        return sum(
            floor.height
            for floor in self.floors[:section_index * FLOORS_PER_SECTION]
        )
