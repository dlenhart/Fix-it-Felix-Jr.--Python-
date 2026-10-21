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
FELIX_FALL_TERMINAL_VEL = 8.0          # _DAT_00416b58
FELIX_HAMMER_START_OFFSET = -7.0       # _DAT_00416b68
FELIX_WALK_START_X_OFFSET = -6.0       # _DAT_00416b08
FELIX_STUN_KNOCKBACK_Y = 480.0         # 0x1e0

# Estimated (runtime-initialized zeros in binary — calibrate during playtesting)
FELIX_HORIZONTAL_ACCEL = 0.5
FELIX_VERTICAL_MOVE_RATE = 1.5         # 36px row spacing in 24 ticks = 0.4s
FELIX_GRAVITY_ACCEL = 0.5
HAMMER_ANIM_RATE = 0.5                 # -7.0 offset to 0 in 14 ticks = 0.23s
BONUS_LIFE_THRESHOLD = 10000

# Estimated durations — authored in seconds so they survive tick-rate changes
SUPER_DURATION_TICKS = seconds_to_ticks(10.0)
HAMMER_EXTENDED_TICKS = seconds_to_ticks(0.1)
STUN_HOLD_TICKS = seconds_to_ticks(1.0)      # pause before rising back up
DYING_TICKS = seconds_to_ticks(1.0)
SPRITE_FRAME_HOLD_TICKS = seconds_to_ticks(0.15)  # walk/flap/idle anim cadence

RALPH_THROW_BASE_INTERVAL_TICKS = seconds_to_ticks(3.0)
RALPH_THROW_INTERVAL_STEP_TICKS = seconds_to_ticks(0.25)  # faster per level
RALPH_THROW_MIN_INTERVAL_TICKS = seconds_to_ticks(0.75)
RALPH_THROW_ANIM_TICKS = seconds_to_ticks(0.5)

BIRD_BASE_INTERVAL_TICKS = seconds_to_ticks(8.0)
BIRD_INTERVAL_STEP_TICKS = seconds_to_ticks(0.5)
BIRD_MIN_INTERVAL_TICKS = seconds_to_ticks(4.0)

PIE_SPAWN_INTERVAL_TICKS = seconds_to_ticks(30.0)
PIE_SPAWN_INTERVAL_STEP_TICKS = seconds_to_ticks(1.0)
PIE_SPAWN_MIN_INTERVAL_TICKS = seconds_to_ticks(20.0)
PIE_LINGER_TICKS = seconds_to_ticks(5.0)
PIE_BLINK_WARNING_TICKS = seconds_to_ticks(1.5)   # blinks for the last 1.5s
BLINK_TOGGLE_TICKS = seconds_to_ticks(0.25)       # pie blink cadence

SECTION_CLEAR_TICKS = seconds_to_ticks(2.0)
TITLE_BLINK_TICKS = seconds_to_ticks(0.5)
GAME_OVER_TICKS = seconds_to_ticks(3.0)
LEVEL_CLEAR_MIN_TICKS = seconds_to_ticks(1.0)   # before JUMP can skip
LEVEL_CLEAR_TICKS = seconds_to_ticks(5.0)

# Entity velocities (Ghidra pass 3)
BRICK_FALL_VEL_A = -1.8               # _DAT_00416b98
BRICK_FALL_VEL_B = -2.2               # _DAT_00416ba4
BRICK_FALL_VEL_C = -1.7               # _DAT_00416ba8
BRICK_DRIFT_X_VEL = 1.7               # _DAT_00416b9c
BIRD_X_VEL = 2.2                      # _DAT_00416b94
BIRD_Y_VEL = -4.0                     # _DAT_00416b90
