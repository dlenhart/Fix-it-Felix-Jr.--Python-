# Exe-numbered ids into exe_tables.SPRITE_FRAMES / BUILDING_PIECES.
PANE_FRAME_INTACT = 163
BRICK_FRAMES = (5, 4)
SILL_OBSTACLE_FRAME = 214
LIFE_ICON_PIECE = 17

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
    "felix_stunned": [(339, 231, 24, 33)],
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
    "pie": [(353, 238, 11, 9)],

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
