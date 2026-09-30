import os

# Internal game resolution (confirmed by Ghidra: 240x320 portrait)
GAME_WIDTH = 240
GAME_HEIGHT = 320

# Display scaling
DISPLAY_SCALE = 3
DISPLAY_WIDTH = GAME_WIDTH * DISPLAY_SCALE   # 720
DISPLAY_HEIGHT = GAME_HEIGHT * DISPLAY_SCALE  # 960

# Timing (confirmed by Ghidra: SetTimer with 250ms)
TICK_RATE = 0.25       # 250ms per game tick
TICKS_PER_SECOND = 4   # Game logic advances 4 times per second
RENDER_FPS = 60        # Display refresh rate

# Ghidra-confirmed constants
INITIAL_LIVES = 10
GRID_COLS = 5
HIGH_SCORE_ENTRIES = 5
HIGH_SCORE_INITIALS = 3
HIGH_SCORE_CHARSET = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."
HS_ENTRY_TIMER_TICKS = 1800   # 30 displayed seconds (÷60)
HS_DISPLAY_TIMER_TICKS = 900
TIME_DISPLAY_DIVISOR = 60     # Ticks per displayed "second"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(PROJECT_ROOT, "Data")
BOOT_DIR = PROJECT_ROOT

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
SKY_BLUE = (92, 148, 252)

# Movement & Physics (Ghidra pass 3 — all in px/tick in 240x320 space)
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
FELIX_VERTICAL_MOVE_RATE = 4.0
FELIX_GRAVITY_ACCEL = 0.5
HAMMER_ANIM_RATE = 1.0
BONUS_LIFE_THRESHOLD = 10000
SUPER_DURATION_TICKS = 40
PIE_SPAWN_INTERVAL_TICKS = 120
BRICK_THROW_BASE_INTERVAL_TICKS = 12

# Entity velocities (Ghidra pass 3)
BRICK_FALL_VEL_A = -1.8               # _DAT_00416b98
BRICK_FALL_VEL_B = -2.2               # _DAT_00416ba4
BRICK_FALL_VEL_C = -1.7               # _DAT_00416ba8
BRICK_DRIFT_X_VEL = 1.7               # _DAT_00416b9c
BIRD_X_VEL = 2.2                      # _DAT_00416b94
BIRD_Y_VEL = -4.0                     # _DAT_00416b90
