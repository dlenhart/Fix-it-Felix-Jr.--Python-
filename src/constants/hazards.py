"""Level-scaled hazards: sill obstacles, birds and Ralph's drop-hazards."""

HAZARD_FLOOR_COUNT = 3  # [EXE] FUN_004067d0 / FUN_00406e00 use the section's top 3 floors
SILL_OBSTACLES_MAX_PER_FLOOR = 2  # [EXE] FUN_00406e00

BIRD_SPEED = 0.5  # [EXE] FUN_00406bb0 px/tick
BIRD_WRAP_LEFT_X = -32  # [EXE] FUN_00406bb0 also the start x of a bird entering from the left
BIRD_WRAP_RIGHT_X = 272  # [EXE] FUN_00406bb0 also the start x of a flipped bird
BIRD_CENTER_ABOVE_FLOOR_BOTTOM = 25  # [ASSUMED] puts the bird at the height of the window glass

DROP_HAZARD_FALL_SPEED = 1.9  # [EXE] FUN_004073f0 px/tick
# TODO: FUN_00409360 caps the hazards *spawned* this section (0x421834, reset per
# section) at the level's limit, plus 3 slots; this caps the live count instead.
DROP_HAZARD_MAX_LIVE = 3  # [EXE] FUN_00409360
# [EXE] FUN_004073f0, after Felix touches it: visibility toggles every 15 ticks
# (timer 0xf, count 4), four visible phases and three hidden, then it is gone.
DROP_HAZARD_BLINKS = 4
DROP_HAZARD_BLINK_HALF_PERIOD_TICKS = 15
DROP_HAZARD_BLINK_TICKS = (2 * DROP_HAZARD_BLINKS - 1) * DROP_HAZARD_BLINK_HALF_PERIOD_TICKS
DROP_HAZARD_SPAWN_DROP = 8  # [EXE] FUN_00409360 spawns at Ralph's y + 8
# [EXE] FUN_004073f0 touch test (0x416b20, 0x416c18): within 4 px across and 5 px
# up or down of the hazard's node, against Felix's own box.
DROP_HAZARD_HALF_WIDTH = 4
DROP_HAZARD_HALF_HEIGHT = 5
DROP_HAZARD_PLACEMENT_ATTEMPTS = 4  # [EXE] FUN_00409360 rerolls a taken floor up to 4 times
# [EXE] FUN_00409360: gaps 1 and 2 flank the center cell; when the section's bottom
# floor has the door there, those gaps only take floors 2 and 3.
DROP_HAZARD_DOOR_SIDE_GAPS = (1, 2)
DROP_HAZARD_DOOR_SIDE_FIRST_FLOOR = 2
