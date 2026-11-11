"""Building model: floors stacked in world coordinates, each with window cells.

Also draws itself (floor art, cell pieces, window panes). Layout follows the exe's
FUN_00405e50 / FUN_00409610, damage FUN_00409840, fix and scoring FUN_00409a70.
"""

import random

import pygame

from audio.sound_sink import SILENT_SOUND, SoundSink
from constants.building import (
    CELL_PIECE_BOTTOM_INSET_Y, DOOR_MAX_DRAWN_DAMAGE, FACADE_X, GLASS_HEIGHT, GLASS_OFFSET_X,
    GLASS_WIDTH, NICELANDER_NODE_ABOVE_SILL_Y, PANE_BOTTOM_OFFSET_Y, PANE_OFFSET_X,
    PANE_TOP_OFFSET_Y, PANE_WINDOW_KINDS, SILL_ROW_IN_PIECE, SILL_SPAN_X, STREET_CLIP_TOP_Y,
    STREET_LAST_STEP, STREET_LEFT_RUN_TILE_OFFSET, STREET_PIECE, STREET_RIGHT_RUN_TILE_OFFSET,
    STREET_STRIP_Y, STREET_TILE_SIZE, STREET_Y,
)
from constants.grid import COLUMN_COUNT, FLOORS_PER_SECTION
from constants.scoring import FIX_LAST_WINDOW_SCORE, FIX_SCORE
from core.camera import Camera
from exe_data.exe_tables import BUILDING_PIECES
from exe_data.level_table import CELL_PIECE, FLOOR_PIECE
from exe_data.sprite_data import PANE_FRAME_INTACT
from graphics.sprite_sheet import SpriteSheet
from world.floor import Floor
from world.level_config import get_floor_sequence, get_level_config
from world.level_types import CellKind, FloorType
from world.window_cell import WindowCell


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
            return CELL_PIECE[CellKind.DOOR] + min(cell.door_damage, DOOR_MAX_DRAWN_DAMAGE)
        return CELL_PIECE[cell.kind]

    def _floor_for_cell(self, cell: WindowCell) -> Floor:
        return self.floors[cell.floor_index]

    def sill_y(self, cell: WindowCell) -> int:
        """World y of the cell's sill (the exe's cell+0x74), the row on top of its ledge.

        Felix stands here: his lowest pixel row is drawn on it. Sill obstacles
        and pies rest on it too, and drop-hazards land at it.
        """
        return self._piece_top_y(cell) + SILL_ROW_IN_PIECE[cell.kind]

    @staticmethod
    def sill_span_x(cell: WindowCell) -> tuple[int, int]:
        """World x bounds (left, right, both inclusive) of the exe's cell (cell+0x6c, +0x70)."""
        left_offset, right_offset = SILL_SPAN_X[cell.kind]
        return cell.x + left_offset, cell.x + right_offset

    @staticmethod
    def sill_middle_x(cell: WindowCell) -> int:
        """The middle of the cell's bounds, where the exe centers what sits on a sill (FUN_00406e00)."""
        left, right = Building.sill_span_x(cell)
        return (right - left) // 2 + left

    def sill_obstacle_node(self, cell: WindowCell) -> tuple[int, int]:
        """Resting point of the cell's sill obstacle node (anim 91's origin, the slab's bottom center).

        x is the exe's (FUN_00406e00). [USER] y is the sill, so the slab rests on
        top of the ledge; the exe hangs it 9 px lower (cell+0x74 + 9), over the
        ledge's face.
        """
        return self.sill_middle_x(cell), self.sill_y(cell)

    def nicelander_node(self, cell: WindowCell) -> tuple[int, int]:
        """Shared node of the cell's Nicelander and its pie (anims 92-97 and 64).

        [EXE] FUN_00407190 puts both at the bottom pane's node plus (5, 9). The
        pane node (FUN_00404ea0) is (X*8+6, EBX*8+0x19) and the sill is
        EBX*8+0x24, so the node is the cell's middle, 2 px above the sill.
        """
        return self.sill_middle_x(cell), self.sill_y(cell) - NICELANDER_NODE_ABOVE_SILL_Y

    def _piece_top_y(self, cell: WindowCell) -> int:
        floor = self._floor_for_cell(cell)
        piece_height = BUILDING_PIECES[CELL_PIECE[cell.kind]][3]
        return floor.bottom_y - self._piece_bottom_inset_y(floor, cell) - piece_height

    @staticmethod
    def _piece_bottom_inset_y(floor: Floor, cell: WindowCell) -> int:
        return CELL_PIECE_BOTTOM_INSET_Y.get((floor.floor_type, cell.kind), 0)

    def glass_rect(self, cell: WindowCell) -> pygame.Rect:
        """World-space rect of the cell's breakable glass.

        Pane windows use the FUN_00404ea0 example rect; the door and arched
        window use their whole piece.
        """
        _, _, piece_width, piece_height = BUILDING_PIECES[CELL_PIECE[cell.kind]]
        piece_top = self._piece_top_y(cell)
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
            screen.blit(floor_surface, (camera.to_screen_x(FACADE_X), screen_top))
            for cell in floor.cells:
                self._draw_cell(screen, sprites, camera, palette, floor, cell)

    def draw_street(
        self,
        screen: pygame.Surface,
        sprites: SpriteSheet,
        camera: Camera,
        palette: int,
    ) -> None:
        """Tile the street strip as FUN_00406050 does; drawn before the building."""
        street = sprites.get_piece(STREET_PIECE, palette)
        screen_y = camera.to_screen_y(STREET_STRIP_Y)
        if screen_y >= screen.get_height():
            return
        crop_top = max(0, STREET_CLIP_TOP_Y - screen_y)
        if crop_top >= street.get_height():
            return
        visible = pygame.Rect(0, crop_top, street.get_width(), street.get_height() - crop_top)
        step_tiles = street.get_width() // STREET_TILE_SIZE
        for tile in range(0, STREET_LAST_STEP + 1, step_tiles):
            for run_offset in (STREET_LEFT_RUN_TILE_OFFSET, STREET_RIGHT_RUN_TILE_OFFSET):
                world_x = (tile + run_offset) * STREET_TILE_SIZE
                screen.blit(street, (camera.to_screen_x(world_x), screen_y + crop_top), visible)

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
        piece_bottom = camera.to_screen_y(floor.bottom_y) - self._piece_bottom_inset_y(floor, cell)
        piece_top = piece_bottom - piece.get_height()
        screen.blit(piece, (camera.to_screen_x(cell.x), piece_top))
        if cell.kind not in PANE_WINDOW_KINDS:
            return
        pane_x = camera.to_screen_x(cell.x + PANE_OFFSET_X)
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
        if not 0 <= section_index < self.section_count:
            raise IndexError(f"section {section_index} outside 0..{self.section_count - 1}")
        start = section_index * FLOORS_PER_SECTION
        return self.floors[start:start + FLOORS_PER_SECTION]

    def cell(self, local_row: int, column: int) -> WindowCell:
        """Return a cell of the active section; local_row 0 is the bottom floor.

        Raises IndexError outside the section's 4 floors and 5 columns.
        """
        if not 0 <= local_row < FLOORS_PER_SECTION:
            raise IndexError(f"local row {local_row} outside 0..{FLOORS_PER_SECTION - 1}")
        if not 0 <= column < COLUMN_COUNT:
            raise IndexError(f"column {column} outside 0..{COLUMN_COUNT - 1}")
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

    def damage(self, cell: WindowCell, is_heavy: bool, sound: SoundSink = SILENT_SOUND) -> None:
        """Damage a cell; breaking an intact window plays "window_break".

        Every damage source goes through FUN_00409840, which plays sound 5 when
        the cell was intact. All its callers (intro wreck, bricks, Ralph's climb)
        ask for the sound.
        """
        was_intact = not cell.is_broken
        cell.damage(is_heavy, self._rng)
        if was_intact and cell.is_broken:
            sound.play_sfx("window_break")

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

    @property
    def roof_top_y(self) -> int:
        """World y of the top of the roof art, the exe's roofY (DAT_0042431c).

        [EXE] FUN_00404870 sets roofY = (top floor +0x2cc) * 8. +0x2cc is the
        floor's top tile row (FUN_00405550: bottom row - height), and the top
        floor is the roof, whose height FUN_00405550 case 4 sets to piece 9's
        height (DAT_004183aa = 20 rows), not our 56 px layout row. Our floors
        sit at the exe's own world y (FUN_00409610 starts at row 0x28 = y 320 =
        STREET_Y and stacks the same heights), so roofY is the roof floor's
        bottom minus the roof art's height.
        """
        roof = self.floors[-1]
        if roof.floor_type != FloorType.ROOF:
            raise RuntimeError(f"top floor is {roof.floor_type!r}, not the roof")
        roof_art_height = BUILDING_PIECES[FLOOR_PIECE[FloorType.ROOF]][3]
        return roof.bottom_y - roof_art_height

    def scroll_target(self, section_index: int) -> int:
        """Camera scroll that brings the section to the screen: heights of floors below it."""
        return sum(
            floor.height
            for floor in self.floors[:section_index * FLOORS_PER_SECTION]
        )
