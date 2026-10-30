# Exe-numbered ids into exe_tables.SPRITE_FRAMES / BUILDING_PIECES.
PANE_FRAME_INTACT = 163
BRICK_FRAMES = (5, 4)
LIFE_ICON_PIECE = 17

# Hazards, read from the exe's animation table at 0x419800. A record's origin is
# the point the sprite node's (x, y) names: FUN_0040ee00 draws the frame's
# top-left at (x - origin_x, y - origin_y).
# [EXE] anim 91 (FUN_00406e00), record (214, -1, 0, 11, 5): the 32x8 slab, art 25x6.
SILL_OBSTACLE_FRAME = 214
SILL_OBSTACLE_ORIGIN = (11, 5)
# [EXE] anim 98, record (215, -1, 0, 11, 14): the brick chunk Ralph drops. FUN_0040a210
# creates the three drop-hazard nodes (0x420ca0, stride 0x24) with anim 0x419c98.
DROP_HAZARD_FRAME = 215
DROP_HAZARD_ORIGIN = (11, 14)

# Felix's hit animations, read from the exe's animation table at 0x419800
# (12-byte entries; each points at 10-byte frame records of
# right-facing frame, left-facing frame or -1, hold, origin x, origin y).
# Holds are the exe's raw counts; FUN_0040ed40 shows each frame hold + 1 ticks.
# [EXE] anim 15 (FUN_0040ca00, lives remain), records at 0x418e50: arms flung out.
FELIX_HIT_FRAMES_RIGHT = (34, 35, 34, 35, 34, 35, 34, 35)
FELIX_HIT_FRAMES_LEFT = (64, 65, 64, 65, 64, 65, 64, 65)
FELIX_HIT_FRAME_HOLD_TICKS = 5
# [EXE] anim 19 (FUN_0040ca00, last life), records at 0x418ee0: Felix tumbles,
# lands flat (72), then lies with the halo (73, 74). It has no left-facing set.
FELIX_FINAL_HIT_FRAMES = (66, 67, 68, 69, 70, 67, 71, 72, 73, 74)
FELIX_FINAL_HIT_FRAME_HOLD_TICKS = (30, 12, 12, 12, 12, 12, 12, 2, 16, 0)

# Nicelanders, read from the exe's animation table at 0x419800. The six
# characters' rise animations are anims 92-97 (the 6-entry table at 0x419e50),
# each 4 records with origin (6, 15), mode 2 (play once, clamp on the last).
# Character n uses peek frame 129 + 2n and bust frame 130 + 2n; the records
# are (peek, bust, bust, peek). Frames are 16x16, the size of a window pane.
NICELANDER_CHARACTER_COUNT = 6  # [EXE] table 0x419e50
NICELANDER_RISE_FRAME_ORDER = (0, 1, 1, 0)  # [EXE] 0 = peek, 1 = bust
NICELANDER_RISE_HOLD_TICKS = (10, 60, 10, 10)  # [EXE] anim 92 records, raw counts
NICELANDER_HANDOFF_FRAME_INDEX = 2  # [EXE] pass 4: the pie appears at animation frame 2
NICELANDER_ORIGIN = (6, 15)  # [EXE] anims 92-97, the art's bottom row


def nicelander_rise_frame_ids(character: int) -> tuple[int, ...]:
    """Exe frame ids of a character's rise animation, in record order."""
    peek_frame_id = 129 + 2 * character
    return tuple(peek_frame_id + order for order in NICELANDER_RISE_FRAME_ORDER)


# [EXE] anim 64 (records at 0x419404): the steaming pie, two frames, hold 10, loops.
# Origin (5, 15) is the pie art's bottom center (art columns 0-10, rows 3-15).
PIE_FRAMES = (156, 157)
PIE_FRAME_HOLD_TICKS = 10
PIE_ORIGIN = (5, 15)

# [EXE] anim 0 (the birds), records at 0x418cd4: mode 1 (loops), two records of
# (right frame, left frame, hold 20, origin 8, 9). Frame sets are right 0, 1 and
# left 2, 3. Which set goes with which travel direction is [ASSUMED]: a bird
# moving right shows the right-facing set.
BIRD_FRAMES_RIGHT = (0, 1)
BIRD_FRAMES_LEFT = (2, 3)
BIRD_FRAME_HOLD_TICKS = 20

SPRITES = {
    # Building tiles
    # Pure-brick region inside the building art, clear of its corner pillar
    # (x<27) and ledge (y 48-54). 64x48 is a whole multiple of the brick
    # pattern's 8x6 repeat, so it tiles seamlessly.
    "wall_brick": [(28, 0, 64, 48)],
    "wall_section_lower": [(9, 172, 190, 20)],
    "window_intact": [(829, 0, 39, 64)],
    "window_cracked": [(421, 48, 39, 64)],
    "window_broken": [(877, 0, 39, 64)],
    "window_frame": [(228, 52, 40, 36)],
    "shutter_left": [],       # no matching art found in atlas; unused by current game code (WINDOW_SPRITE_MAP doesn't reference shutters)
    "shutter_right": [],      # same as above
    "niceland_sign": [(421, 48, 39, 26)],
    "ledge": [(7, 0, 10, 30)],

    # Felix animations — each list has multiple frames
    "felix_idle_right": [(68, 232, 12, 32)],
    "felix_idle_left": [(80, 328, 12, 32)],
    "felix_walk_right": [(2, 231, 15, 33), (32, 230, 19, 32), (68, 232, 12, 32), (96, 230, 19, 32)],
    "felix_walk_left": [(15, 327, 15, 33), (45, 326, 19, 32), (80, 328, 12, 32), (109, 326, 19, 32)],
    "felix_climb_up": [(138, 323, 26, 37)],
    "felix_climb_down": [(132, 227, 26, 37)],
    # Felix's atlas art is two complete facing sets: the y~230 row faces
    # right (its strike swings right), the y~326 row is its mirror. Hammer
    # frames must come from the same row as the matching idle/walk frames.
    "felix_hammer_right": [(168, 228, 25, 34), (204, 230, 21, 34), (232, 228, 25, 34), (264, 230, 25, 34)],
    "felix_hammer_left": [(175, 324, 25, 34), (207, 326, 21, 34), (239, 324, 25, 34), (271, 326, 25, 34)],
    # Strike = hammer swung out sideways; bbox includes the detached impact sparkle
    "felix_strike_right": [(298, 232, 35, 32)],
    "felix_strike_left": [(299, 328, 35, 32)],
    "felix_celebrate": [(3, 279, 18, 33), (35, 277, 16, 35)],
    "felix_head": [(68, 232, 12, 14)],

    # Ralph animations
    "ralph_idle": [(11, 426, 45, 54), (72, 425, 43, 55)],
    "ralph_smash": [(826, 898, 59, 62), (892, 897, 61, 63)],
    "ralph_throw": [(0, 509, 66, 43), (145, 509, 66, 43)],
    "ralph_climb": [(193, 430, 63, 50), (257, 431, 63, 49)],
    "ralph_fall": [(1, 631, 66, 68), (72, 632, 68, 66)],
    "ralph_face": [(11, 426, 45, 30)],

    # Hazards and items
    "brick_falling": [(920, 16, 23, 27)],
    "bird_right": [(336, 24, 21, 13)],
    "bird_left": [(360, 30, 21, 13)],

    # UI elements
    "title_logo": [(226, 114, 184, 70)],
    "medal_bronze": [(517, 0, 57, 96)],
    "medal_silver": [(581, 0, 57, 96)],
    "medal_gold": [(645, 0, 57, 96)],

    # Cutscene elements
    "building_exterior": [(295, 804, 210, 156)],
    "tree_left": [(512, 630, 80, 130)],
    "tree_right": [(672, 630, 80, 130)],
    "cloud": [(520, 544, 51, 20)],
    "ralph_cutscene_idle": [(516, 762, 43, 54)],
    "ralph_cutscene_smash": [(552, 820, 64, 79)],
    "nicelander_head": [(2, 861, 11, 19), (17, 862, 11, 18), (32, 863, 13, 17), (48, 862, 13, 18)],
}

# Head-center x within frame 0 of Felix's hammer sprites. These frames are
# wider than the body (the hammer sticks out to one side), so centering the
# whole frame on the window would shift Felix sideways mid-swing; aligning
# the head instead keeps his body planted. Measured from the atlas.
FELIX_HEAD_CENTER_X = {
    "felix_hammer_right": 9,
    "felix_hammer_left": 15,
    "felix_strike_right": 7,
    "felix_strike_left": 27,
}

# Font definition — 4 color rows of bitmap characters
# Each row starts at a y-offset, characters are 8px wide, 8px tall
# Character order matches ASCII from '!' (0x21) onward
FONT_ROWS = {
    0: {"y": 968, "char_width": 8, "char_height": 8, "start_x": 8},
    1: {"y": 976, "char_width": 8, "char_height": 8, "start_x": 8},
    2: {"y": 984, "char_width": 8, "char_height": 8, "start_x": 8},
    3: {"y": 992, "char_width": 8, "char_height": 8, "start_x": 8},
}

# Hammer effect sprites (from hammer0-3.png)
HAMMER_SPRITES = {
    "hammer_swing": [(150, 227, 8, 14), (185, 228, 8, 13), (217, 230, 8, 13), (249, 228, 8, 13)],
    "repair_sparkle": [(514, 909, 62, 64), (584, 914, 51, 52), (643, 916, 45, 46), (704, 918, 37, 38)],
}
