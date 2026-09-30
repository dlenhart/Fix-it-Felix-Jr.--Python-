SPRITES = {
    # Building tiles
    "wall_brick": [],
    "wall_section_lower": [],
    "window_intact": [],
    "window_cracked": [],
    "window_broken": [],
    "window_frame": [],
    "shutter_left": [],
    "shutter_right": [],
    "niceland_sign": [],
    "ledge": [],

    # Felix animations — each list has multiple frames
    "felix_idle_right": [],
    "felix_idle_left": [],
    "felix_walk_right": [],
    "felix_walk_left": [],
    "felix_climb_up": [],
    "felix_climb_down": [],
    "felix_hammer_right": [],
    "felix_hammer_left": [],
    "felix_hammer_up": [],
    "felix_stunned": [],
    "felix_celebrate": [],
    "felix_head": [],

    # Ralph animations
    "ralph_idle": [],
    "ralph_smash": [],
    "ralph_throw": [],
    "ralph_climb": [],
    "ralph_fall": [],
    "ralph_face": [],

    # Hazards and items
    "brick_falling": [],
    "bird_right": [],
    "bird_left": [],
    "pie": [],

    # UI elements
    "title_logo": [],
    "medal_bronze": [],
    "medal_silver": [],
    "medal_gold": [],

    # Cutscene elements
    "building_exterior": [],
    "tree_left": [],
    "tree_right": [],
    "cloud": [],
    "ralph_cutscene_idle": [],
    "ralph_cutscene_smash": [],
    "nicelander_head": [],
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
    "hammer_swing": [],
    "repair_sparkle": [],
}
