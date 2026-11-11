"""Building geometry: facade, street strip, panes, glass, sills and sill obstacles."""

from types import MappingProxyType

from world.level_types import CellKind, FloorType

FACADE_X = 8  # [EXE] floor art is drawn at x = 8
STREET_Y = 320  # [EXE] FUN_00409610: the ground floor's bottom is tile row 0x28, the screen bottom

# [EXE] FUN_00406050: building piece 1 tiled along the street, two runs per step.
STREET_PIECE = 1
STREET_TILE_SIZE = 8
STREET_LAST_STEP = 0x1E  # the step loop runs while the tile index is <= 0x1e
STREET_LEFT_RUN_TILE_OFFSET = -0x1C
STREET_RIGHT_RUN_TILE_OFFSET = 0x1A
STREET_STRIP_Y = 0x130  # screen y = camera y + 0x130
STREET_CLIP_TOP_Y = 0x18  # rows above y 0x18 are cropped off (the HUD band)

PANE_INTACT = 0
PANE_SMASHED = 5  # [EXE] FUN_00409840: pane state 5 is fully smashed
PANE_DAMAGE_MAX = PANE_SMASHED  # [EXE] FUN_00409840: light damage rolls 1..5

DOOR_MAX_DRAWN_DAMAGE = 3  # [ASSUMED] door art has 4 pieces: intact + 3 damage steps
PANE_TOP_OFFSET_Y = 0xC  # [EXE] FUN_00404ea0 top pane, from the cell piece top
PANE_BOTTOM_OFFSET_Y = 0x19  # [EXE] FUN_00404ea0 bottom pane
# [EXE] FUN_00407190: the Nicelander/pie node, bottom pane node + 9 = sill - 2.
NICELANDER_NODE_ABOVE_SILL_Y = 2
# [EXE] FUN_00404ea0 puts the pane nodes at X*8+6 (types 0/3) and X*8+10 (type 4,
# whose piece is drawn at X*8+4), with anim 66's origin (0, 0): cell.x + 6.
PANE_OFFSET_X = 6
PANE_WINDOW_KINDS = (CellKind.PLAIN, CellKind.PEDIMENT_A, CellKind.PEDIMENT_B)
GLASS_OFFSET_X = 6  # [EXE] FUN_00404ea0 example rect
GLASS_WIDTH = 12  # [EXE] FUN_00404ea0 example rect
GLASS_HEIGHT = 23  # [EXE] FUN_00404ea0 example rect

# [EXE] FUN_00404ea0: the cell's horizontal bounds (cell+0x6c, cell+0x70), as
# offsets from the drawn piece's left edge. Pane types 0/3 store X*8 .. X*8+0x17;
# type 4 stores X*8+4 .. X*8+0x1b but its piece is drawn 4px right
# (FUN_0040f0a0: X*8+4), so all pane kinds come out at 0..23. The door and the
# arched window store X*8+4 .. X*8+0x2b.
SILL_SPAN_X: MappingProxyType[CellKind, tuple[int, int]] = MappingProxyType({
    CellKind.PLAIN: (0, 0x17),
    CellKind.PEDIMENT_A: (0, 0x17),
    CellKind.PEDIMENT_B: (0, 0x17),
    CellKind.DOOR: (4, 0x2B),
    CellKind.ARCHED: (4, 0x2B),
})

# [EXE] the per-cell sill y (cell+0x74), the y the exe stands Felix on, as a row
# of the cell's piece. Felix's anims put their last frame row on that y (origin
# y 47 on 48-tall frames), so his lowest pixel row sits on it.
# - Pane types: FUN_00404ea0 stores EBX*8 + 0x24 and FUN_00405ca0 draws the
#   piece at row EBX (FUN_0040ef90), so row 36, the row on top of the ledge
#   (rows 37-42).
# - The door (0x138) and the arched window (0xfd) store world y. FUN_00409610
#   starts the ground floor's bottom at tile row 0x28, y 320 = our STREET_Y, so
#   the exe's world y is ours. FUN_00405550 draws the door at the ground floor's
#   top row - 1 (y 0x100) and the arched window at the second floor's top
#   row + 1 (y 0xd8): rows 56 (on top of the steps, rows 57-63) and 37 (inside
#   the balustrade, rows 32-39).
SILL_ROW_IN_PIECE: MappingProxyType[CellKind, int] = MappingProxyType({
    CellKind.PLAIN: 0x24,
    CellKind.PEDIMENT_A: 0x24,
    CellKind.PEDIMENT_B: 0x24,
    CellKind.DOOR: 0x138 - 0x100,
    CellKind.ARCHED: 0xFD - 0xD8,
})

# [EXE] FUN_00405550 draws the ground floor's pane cells at the floor's top row
# and the arched window at the second floor's top row + 1, so both end 8 px
# above their floor's bottom. Every other cell piece (the door, the second
# floor's panes, both brick floors) ends on its floor's bottom.
CELL_PIECE_BOTTOM_INSET_Y: MappingProxyType[tuple[FloorType, CellKind], int] = MappingProxyType({
    (FloorType.GROUND, CellKind.PLAIN): 8,
    (FloorType.SECOND, CellKind.ARCHED): 8,
})

# [EXE] FUN_004070f0, table 0x419e40: a bumped sill obstacle's y offset steps
# through -4, -2 and -1, 4 ticks each, then rests at 0 again.
SILL_OBSTACLE_BOUNCE_OFFSETS_Y = (-4, -2, -1)
SILL_OBSTACLE_BOUNCE_STEP_TICKS = 4
SILL_OBSTACLE_BOUNCE_TICKS = len(SILL_OBSTACLE_BOUNCE_OFFSETS_Y) * SILL_OBSTACLE_BOUNCE_STEP_TICKS
