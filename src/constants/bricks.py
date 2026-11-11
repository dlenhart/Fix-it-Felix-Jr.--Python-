"""Bricks. FUN_0040d490 (fall, window breaks), FUN_0040d3e0 (bounce), FUN_0040dd90 (spawn)."""

BRICK_SPAWN_SPREAD = 32  # [EXE] FUN_0040dd90 x offset is rand(-32..31)
BRICK_SPAWN_DROP = 8  # [EXE] FUN_0040dd90 y offset below Ralph's feet

BRICK_WIDTH = 16
BRICK_HEIGHT = 24  # frame 5 (16x16) with frame 4 (16x8) stacked on top, [ASSUMED] stacking

GROUND_Y = 317  # [EXE] FUN_0040d490 world y at which a falling brick bounces
BRICK_FALL_SPEED = 1.9  # [EXE] FUN_0040d490 px/tick, straight down
BRICK_MAX_LIVE = 64  # [EXE] FUN_0040d490 brick slot count
BRICK_WINDOW_BREAK_ODDS = 200  # [EXE] FUN_0040d490 1-in-200 per overlapping tick
BRICK_WINDOW_BREAK_ROLL = 99  # [EXE] FUN_0040d490 the winning value of the 1-in-200 roll
BRICK_WINDOW_BREAK_MIN_LEVEL = 2  # [EXE] FUN_0040d490
BRICK_WINDOW_BREAKS_PER_SECTION = 4  # [EXE] FUN_0040d490 cap; reset per section is [ASSUMED]
BRICK_BOUNCE_VX = 1.3  # [EXE] FUN_0040d3e0 sign is a coin flip
BRICK_BOUNCE_VY = -3.0  # [EXE] FUN_0040d3e0
BRICK_BOUNCE_GRAVITY = 0.4  # [EXE] FUN_0040d3e0 px/tick^2
BRICK_BOUNCE_TICKS = 40  # [ASSUMED] bounce lifetime before the brick vanishes
BRICK_BLINK_TICKS = 4  # [ASSUMED] visible/hidden period while bouncing, matches Felix's blink
