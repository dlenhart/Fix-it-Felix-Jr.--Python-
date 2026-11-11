"""Felix: lives, movement, hammer, hit sequence and invulnerability.

Movement is in px/tick in 240x320 space (Ghidra pass 3). At 60 ticks/sec,
2.0 px/tick crosses one window (40 px) in 20 ticks = 0.33s.
"""

from constants.timing import seconds_to_ticks

INITIAL_LIVES = 10  # [USER] kept at 10; the exe starts with 3 (2 spares, 0x00407676)
INVULNERABLE_TICKS = 480  # [EXE] 0x4217a4 timer (pie)
INVULNERABLE_BLINK_TICKS = 4

HITBOX_WIDTH = 12  # [ASSUMED]
HITBOX_HEIGHT = 28  # [ASSUMED]

FELIX_MAX_HORIZONTAL_SPEED = 2.0  # [EXE] _DAT_00416b40
FELIX_HAMMER_START_OFFSET = -7.0  # [EXE] _DAT_00416b68
# Estimated: runtime-initialized zeros in the binary, calibrated by playtesting.
FELIX_HORIZONTAL_ACCEL = 0.5  # [ASSUMED] _DAT_00416b80 is runtime-initialized
FELIX_VERTICAL_MOVE_RATE = 1.5  # [ASSUMED] estimated from playtest feel, exe jump is a gravity arc; 36px row spacing in 24 ticks = 0.4s
HAMMER_ANIM_RATE = 0.5  # [ASSUMED] estimated, exe rate not decoded; -7.0 offset to 0 in 14 ticks = 0.23s
# Estimated durations, authored in seconds so they survive tick-rate changes.
HAMMER_EXTENDED_TICKS = seconds_to_ticks(0.1)  # [ASSUMED] estimated hold, exe value not decoded
SPRITE_FRAME_HOLD_TICKS = seconds_to_ticks(0.15)  # [ASSUMED] estimated cadence, exe not decoded; walk/flap/idle anim cadence

# [EXE] double at 0x416be8: the hit fall (FUN_0040c1a0) and the fall back from a
# bumped jump (FUN_0040c0d0) both add it to vy each tick.
FELIX_HIT_FALL_GRAVITY = 0.33
FELIX_FALL_MAX_SPEED = 8.0  # [EXE] FUN_0040c0d0 caps vy at 0x416b58
# [EXE] FUN_0040bea0 (0x416b60 = 36.0): a rising jump bumps once y - 36 (5 px
# above Felix's hat) reaches the y of the sill obstacle's node above.
FELIX_BUMP_POINT_ABOVE_FEET = 36
FELIX_HIT_FALL_BELOW_STREET = 0x28  # [EXE] FUN_0040c1a0: building bottom + 0x28
FELIX_RESPAWN_DELAY_TICKS = 60  # [EXE] FUN_0040c1a0 (0x3c)
FELIX_FINAL_HIT_SETTLE_FRAME_INDEX = 7  # [EXE] FUN_0040c1a0 waits for anim frame 7
FELIX_GAME_OVER_DELAY_TICKS = 120  # [EXE] FUN_0040c1a0 (0x78) before the game-over state
