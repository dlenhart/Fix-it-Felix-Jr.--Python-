"""Ralph's state machine.

[EXE] 0x40e1a4 (state table), FUN_0040d870 (patrol/pound), FUN_0040d970 (rage),
FUN_0040dbb0 (climb), FUN_0040dd90 (brick spawn).
"""

RALPH_WALK_SPEED = 1.0  # [EXE] 0x40e1a4 walk, px/tick
RALPH_PATROL_CENTER_X = 120  # [EXE] 0x40e1a4 start and hub position
RALPH_PATROL_SIDE_X = (72, 169)  # [EXE] 0x40e1a4 alternating stops
RALPH_POUND_BASE_TICKS = 9  # [EXE] FUN_0040d870 first brick countdown; FUN_0040d970 interval floor
RALPH_POUND_RANDOM_TICKS = 8  # [EXE] FUN_0040d970 rand() & 7 added to the interval
RALPH_POUND_ARRIVALS_PER_DROP = 3  # [EXE] FUN_0040d870 DAT_00421740 counts arrivals down from 3
RALPH_DROP_DELAY_TICKS = 30  # [EXE] FUN_0040d870 DAT_00421744 = 0x1e, counted by FUN_0040d970
RALPH_CLIMB_SPEED = 1.0  # [EXE] FUN_0040dbb0 px/tick
RALPH_CLIMB_DAMAGE_INTERVAL_TICKS = 10  # [EXE] FUN_0040dbb0
RALPH_CLIMB_DAMAGE_CHANCE = 0.5  # [EXE] FUN_0040dbb0
RALPH_RAGE_WINDUP_TICKS = 80  # [EXE] FUN_0040d970
RALPH_RAGE_BRICK_INTERVAL_TICKS = 8  # [EXE] FUN_0040d970
RALPH_RAGE_DURATION_TICKS = 240  # [EXE] FUN_0040d970
RALPH_SECTION_CLIMB_WAIT_TICKS = 0x78  # [EXE] FUN_0040e0e1: Ralph waits (still posing) before climbing

# [EXE] FUN_0040d970 / FUN_0040dd90 restart the smash sound when the node has
# just moved onto one of these frames.
POUND_SMASH_FRAMES = (0x52, 0x54)
RAGE_SMASH_FRAMES = (0x56, 0x57)
# [EXE] FUN_0040d970 leaves its wind-up phase (DAT_00421738 0 -> 1) once past frame 1.
POUND_LAST_WINDUP_FRAME_INDEX = 1
