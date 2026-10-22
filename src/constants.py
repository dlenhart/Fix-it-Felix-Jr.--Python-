import os

# Internal game resolution (confirmed by Ghidra: 240x320 portrait)
GAME_WIDTH = 240
GAME_HEIGHT = 320

# Display scaling
DISPLAY_SCALE = 3
DISPLAY_WIDTH = GAME_WIDTH * DISPLAY_SCALE   # 720
DISPLAY_HEIGHT = GAME_HEIGHT * DISPLAY_SCALE  # 960

# Timing — game logic runs at 60 ticks/sec. The original binary's 250ms
# SetTimer (FUN_00413de0) only updates the window title, not game logic
# (Ghidra pass 3). 60 Hz is inferred from the confirmed timer values below:
# 60 ticks per displayed second, 1800-tick (30s) high-score entry, etc. —
# at 4 Hz those would be 15s "seconds" and a 7.5-minute entry timer.
TICKS_PER_SECOND = 60
TICK_RATE = 1.0 / TICKS_PER_SECOND   # seconds per game tick
RENDER_FPS = 60                      # Display refresh rate


def seconds_to_ticks(seconds):
    """Convert a real-time duration to a whole number of game ticks."""
    return round(seconds * TICKS_PER_SECOND)


# Ghidra-confirmed constants
INITIAL_LIVES = 10
GRID_COLS = 5
HIGH_SCORE_ENTRIES = 5
HIGH_SCORE_INITIALS = 3
HIGH_SCORE_CHARSET = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."
HS_ENTRY_TIMER_TICKS = 1800   # 30 displayed seconds (÷60)
HS_DISPLAY_TIMER_TICKS = 900   # 15 seconds
TIME_DISPLAY_DIVISOR = 60     # Ticks per displayed "second"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(PROJECT_ROOT, "Data")
BOOT_DIR = PROJECT_ROOT

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
SKY_BLUE = (92, 148, 252)

# Movement & Physics (Ghidra pass 3 — all in px/tick in 240x320 space)
# At 60 ticks/sec, 2.0 px/tick crosses one window (WINDOW_SPACING_X=40) in
# 20 ticks = 0.33s.
FELIX_MAX_HORIZONTAL_SPEED = 2.0       # _DAT_00416b40
FELIX_INITIAL_VERTICAL_VEL = 0.2       # _DAT_00416b88
FELIX_JUMP_INITIAL_X_VEL = -5.0        # _DAT_00416c00
FELIX_JUMP_ARC_DIVISOR = 10.0          # _DAT_00416c04
FELIX_HAMMER_START_OFFSET = -7.0       # _DAT_00416b68
FELIX_WALK_START_X_OFFSET = -6.0       # _DAT_00416b08

# Estimated (runtime-initialized zeros in binary — calibrate during playtesting)
FELIX_HORIZONTAL_ACCEL = 0.5           # [ASSUMED] _DAT_00416b80 is runtime-initialized
FELIX_VERTICAL_MOVE_RATE = 1.5         # 36px row spacing in 24 ticks = 0.4s
HAMMER_ANIM_RATE = 0.5                 # -7.0 offset to 0 in 14 ticks = 0.23s
BONUS_LIFE_THRESHOLD = 5000            # [EXE string "BONUS LIFE EVERY 5000 PTS"]
INVULNERABLE_TICKS = 480               # [EXE] 0x4217a4 timer (pie)

# Estimated durations — authored in seconds so they survive tick-rate changes
HAMMER_EXTENDED_TICKS = seconds_to_ticks(0.1)
SPRITE_FRAME_HOLD_TICKS = seconds_to_ticks(0.15)  # walk/flap/idle anim cadence

# Ralph state machine. [EXE] 0x40e1a4 (state table), FUN_0040d870 (patrol/pound),
# FUN_0040d970 (rage), FUN_0040dbb0 (climb), FUN_0040dd90 (brick spawn).
RALPH_WALK_SPEED = 1.0  # [EXE] 0x40e1a4 walk, px/tick
RALPH_PATROL_CENTER_X = 120  # [EXE] 0x40e1a4 start and hub position
RALPH_PATROL_SIDE_X = (72, 169)  # [EXE] 0x40e1a4 alternating stops
RALPH_POUND_BASE_TICKS = 9  # [EXE] FUN_0040d870 brick interval floor
RALPH_POUND_RANDOM_TICKS = 8  # [EXE] FUN_0040d870 rand(0..7) added to the interval
RALPH_POUND_DURATION_TICKS = 60  # [ASSUMED] exe pound duration is open in the spec
RALPH_CYCLES_PER_DROP = 3  # [EXE] FUN_0040d870 walk/pound cycles per drop hazard
RALPH_DROP_DELAY_TICKS = 30  # [EXE] FUN_0040d870 timer before the drop hazard
RALPH_CLIMB_SPEED = 1.0  # [EXE] FUN_0040dbb0 px/tick
RALPH_CLIMB_DAMAGE_INTERVAL_TICKS = 10  # [EXE] FUN_0040dbb0
RALPH_CLIMB_DAMAGE_CHANCE = 0.5  # [EXE] FUN_0040dbb0
RALPH_RAGE_WINDUP_TICKS = 80  # [EXE] FUN_0040d970
RALPH_RAGE_BRICK_INTERVAL_TICKS = 8  # [EXE] FUN_0040d970
RALPH_RAGE_DURATION_TICKS = 240  # [EXE] FUN_0040d970
RALPH_SECTION_POSE_TICKS = 60  # [ASSUMED] pose length; timed by the game scene
BRICK_SPAWN_SPREAD = 32  # [EXE] FUN_0040dd90 x offset is rand(-32..31)
BRICK_SPAWN_DROP = 8  # [EXE] FUN_0040dd90 y offset below Ralph's feet


TITLE_BLINK_TICKS = seconds_to_ticks(0.5)
GAME_OVER_TICKS = seconds_to_ticks(3.0)

# Bricks. FUN_0040d490 (fall, window breaks), FUN_0040d3e0 (bounce), FUN_0040d230 (Felix hit).
GROUND_Y = 317  # [EXE] FUN_0040d490 world y at which a falling brick bounces
BRICK_FALL_SPEED = 1.9  # [EXE] FUN_0040d490 px/tick, straight down
BRICK_MAX_LIVE = 64  # [EXE] FUN_0040d490 brick slot count
BRICK_WINDOW_BREAK_ODDS = 200  # [EXE] FUN_0040d490 1-in-200 per overlapping tick
BRICK_WINDOW_BREAK_MIN_LEVEL = 2  # [EXE] FUN_0040d490
BRICK_WINDOW_BREAKS_PER_SECTION = 4  # [EXE] FUN_0040d490 cap; reset per section is [ASSUMED]
BRICK_BOUNCE_VX = 1.3  # [EXE] FUN_0040d3e0 sign is a coin flip
BRICK_BOUNCE_VY = -3.0  # [EXE] FUN_0040d3e0
BRICK_BOUNCE_GRAVITY = 0.4  # [EXE] FUN_0040d3e0 px/tick^2
BRICK_BOUNCE_TICKS = 40  # [ASSUMED] bounce lifetime before the brick vanishes
BRICK_BLINK_TICKS = 4  # [ASSUMED] visible/hidden period while bouncing, matches Felix's blink
