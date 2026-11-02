"""Exe data for the roof ending (game state 6) and the game-end screen.

Every value is [EXE]: decoded from FixitFelixJr.exe (see
.superpowers/sdd/2026-10-21-gameplay-rebuild/roof-decode.md and task-11b-report.md).
No pygame dependency.
"""

from dataclasses import dataclass
from enum import IntEnum


class AnimationMode(IntEnum):
    """Animation table field +4, as FUN_0040ed40 reads it."""
    STATIC = 0  # never advances
    LOOP = 1  # wraps to frame 0
    ONCE = 2  # clamps on the last frame and sets the node's "finished" flag


@dataclass(frozen=True)
class AnimationFrame:
    """One 10-byte frame record: right-facing frame id, hold, origin.

    The left-facing id is omitted: no roof node faces left (FUN_00404870
    clears flag bit 2 on Felix; the other nodes start with it clear).
    FUN_0040ee00 draws the frame's top-left at (x - origin_x, y - origin_y).
    """
    frame_id: int
    hold: int
    origin_x: int
    origin_y: int


@dataclass(frozen=True)
class Animation:
    """One entry of the exe animation table at 0x419800 (12 bytes each)."""
    mode: AnimationMode
    frames: tuple[AnimationFrame, ...]


def _animation(mode: AnimationMode, *records: tuple[int, int, int, int]) -> Animation:
    return Animation(mode, tuple(AnimationFrame(*record) for record in records))


# [EXE] animation table 0x419800, read from the exe bytes. Records are
# (right frame, hold, origin x, origin y).
ROOF_ANIMATIONS: dict[int, Animation] = {
    2: _animation(AnimationMode.STATIC, (6, 0, 44, 39)),  # cloud
    3: _animation(AnimationMode.STATIC, (7, 0, 10, 47)),  # Felix standing
    5: _animation(AnimationMode.STATIC, (36, 0, 10, 47)),  # Felix looks at the door
    6: _animation(AnimationMode.LOOP, (27, 10, 10, 47), (28, 10, 10, 47)),  # eating the pie
    7: _animation(AnimationMode.LOOP, (30, 10, 10, 47), (29, 10, 10, 47)),  # kissed
    16: _animation(AnimationMode.ONCE, (31, 10, 10, 47), (32, 10, 10, 47)),  # hammer raised
    17: _animation(AnimationMode.ONCE, (26, 10, 10, 47), (27, 10, 10, 47), (28, 10, 10, 47)),
    18: _animation(AnimationMode.STATIC, (25, 0, 10, 47)),  # wearing the medal
    29: _animation(AnimationMode.ONCE, (90, 0, 33, 71)),  # Ralph standing
    30: _animation(AnimationMode.ONCE, (91, 0, 33, 71)),  # Ralph carried, lying
    31: _animation(AnimationMode.LOOP, (94, 8, 33, 71), (95, 8, 33, 71), (92, 8, 33, 71),
                   (93, 8, 33, 71)),  # Ralph tumbling
    32: _animation(AnimationMode.ONCE, (96, 10, 50, 38), (97, 10, 50, 38),
                   (98, 10, 50, 38)),  # Ralph lands in the mud
    50: _animation(AnimationMode.LOOP, (141, 6, 6, 23), (141, 6, 6, 24)),
    51: _animation(AnimationMode.LOOP, (142, 6, 6, 24), (142, 6, 6, 23)),
    52: _animation(AnimationMode.LOOP, (143, 6, 6, 23), (143, 6, 6, 24)),
    53: _animation(AnimationMode.LOOP, (144, 6, 6, 24), (144, 6, 6, 23)),
    54: _animation(AnimationMode.LOOP, (145, 6, 6, 23), (145, 6, 6, 24)),
    56: _animation(AnimationMode.STATIC, (147, 0, 6, 23)),  # frowning
    57: _animation(AnimationMode.STATIC, (148, 0, 6, 23)),
    58: _animation(AnimationMode.STATIC, (149, 0, 6, 23)),
    59: _animation(AnimationMode.STATIC, (150, 0, 6, 23)),
    60: _animation(AnimationMode.STATIC, (151, 0, 6, 23)),
    62: _animation(AnimationMode.ONCE, (153, 10, 22, 23), (154, 0, 14, 23)),  # holds out the pie
    63: _animation(AnimationMode.ONCE, (141, 9, 6, 23), (141, 9, 6, 27), (141, 9, 6, 35),
                   (155, 9, 2, 35), (155, 9, 4, 35), (141, 9, 6, 29),
                   (141, 9, 6, 23)),  # jumps up to kiss Felix
    70: _animation(AnimationMode.ONCE, (178, 10, 0, 0), (179, 30, 0, 0), (180, 30, 0, 0)),  # hatch
    71: _animation(AnimationMode.ONCE, (181, 20, 32, 95), (182, 20, 32, 95), (183, 20, 32, 95),
                   (184, 60, 32, 95), (184, 4, 40, 87), (185, 4, 48, 33),
                   (186, 4, 48, -3)),  # the medal
}

# --- Setup, FUN_00404870 -----------------------------------------------------
# Camera for phase 0 (DAT_0041a298 = 0xff10, DAT_0041a248 = 0x10).
PHASE_0_SCROLL = (-240, 16)
FELIX_ANIM_HAMMER_RAISED = 16
FELIX_PHASE_0_NODE = (360, 168, 50)  # (x, y, z)
CLOUD_ANIM = 2
LEFT_CLOUD_X = 0x68  # DAT_00424320, node DAT_004242f0
LEFT_CLOUD_ABOVE_ROOF_Y = 0x10
LEFT_CLOUD_Z = 0x78
RIGHT_CLOUD_X = 0x80  # DAT_00424324, node DAT_004242f4
RIGHT_CLOUD_ABOVE_ROOF_Y = 0x18
RIGHT_CLOUD_Z = 100
DOOR_ANIM = 70  # node DAT_004242ec, visible and paused
DOOR_X = 0x10
DOOR_Z = 200
MEDAL_ANIM = 71  # node DAT_004242f8, paused and hidden
MEDAL_X = 0x78
MEDAL_ABOVE_ROOF_Y = 0x10
MEDAL_Z = 0x6E
NICELANDER_FIRST_ANIM = 0x32  # nodes DAT_004242c0..d0 get anims 50..54
NICELANDER_COUNT = 5
NICELANDER_START_X = -61  # DAT_00424314 = 0xffffffc3
NICELANDER_STOP_X = 0x3B  # DAT_00424318
# FUN_004047f0: in phase 1 a Nicelander shows once its x passes the hatch.
NICELANDER_VISIBLE_AFTER_X = 0x1B
# Roof music, FUN_0040f4a0 with loop flag 0 in every case.
PHASE_0_MUSIC = 0xB  # FUN_00404870 / FUN_00404610(0)
PHASE_1_MUSIC = 0xC  # FUN_00404610(1)
PHASE_2_MUSIC = 0xD  # FUN_00404610(2), ESI = EDI + 0xd
# FUN_00408fc0 case 6 stops sound 0x18 before the setup.
STATE_ENTRY_STOPPED_SOUND = 0x18

# --- Phase 0, FUN_004039d0 / FUN_00403a20 -------------------------------------
PHASE_0_TICKS = 0xB4
PHASE_0_MESSAGE = "YOU FIXED IT!"  # string 0x416314
PHASE_0_MESSAGE_COLUMN = 0x27
PHASE_0_MESSAGE_ROW = 0xD
PHASE_0_MESSAGE_FIRST_COLOUR = 2  # EBX = DAT_00424328 + 2
PHASE_0_COLOUR_STEPS = 6  # DAT_00424328 cycles 0..5
PHASE_0_COLOUR_FRAME_MASK = 3  # it steps when (frame counter & 3) == 0

# --- Phase 1, FUN_00404610(1) and the step script FUN_00403a40 ----------------
PHASE_1_ROOF_SCROLL_Y = 0x70  # DAT_0041a248 = 0x70 - roofY; DAT_0041a298 = 0
ACTOR_BELOW_ROOF_Y = 0x1C  # Felix, Ralph and the Nicelanders stand at roofY + 0x1c
FELIX_ANIM_STANDING = 3
FELIX_PHASE_1_X = 0x4B
FELIX_PHASE_1_Z = 100
RALPH_ANIM_STANDING = 29
RALPH_PHASE_1_X = 0xAF
RALPH_Z = 0x96
NICELANDER_Z = 0xA0
# Step 0
FELIX_ANIM_LOOKS_AT_DOOR = 5
# Step 1: every 3 ticks the line moves 4 px.
WALK_OUT_STEP_TICKS = 3
WALK_OUT_STEP_X = 4
WALK_OUT_OFFSETS_X = (0, 0x29, 0x37, 0x45, 0x53)
# Step 2: every 5 ticks the clouds part by 6 px each.
CLOUD_STEP_TICKS = 5
CLOUD_STEP_X = 6
FELIX_ANIM_WEARING_MEDAL = 0x12
# Step 3
PIE_WAIT_TICKS = 0x1E
PIE_GIVER_INDEX = 1  # node DAT_004242c4
PIE_GIVER_ANIM = 0x3E
FELIX_ANIM_TAKES_PIE = 0x11
# Step 4
FELIX_ANIM_EATS_PIE = 6
PIE_GIVER_IDLE_ANIM = 0x33
KISSER_INDEX = 0  # node DAT_004242c0
KISSER_ANIM = 0x3F
# Step 5
KISS_FRAME_INDEX = 3  # node +0x12 == 3
FELIX_ANIM_KISSED = 7
KISS_SOUND = 0x1A
FROWN_WAIT_TICKS = 0x32
FROWN_FIRST_ANIM = 0x38  # anims 56..60
# Steps 6 and 7: one move every 3 ticks; footstep sound on every 4th move.
MARCH_START_DELAY_TICKS = 0x3C  # step 6 moves once its counter passes 60
MARCH_STEP_TICKS = 3
MARCH_STEP_X = 3
FOOTSTEP_SOUND = 0x1B
FOOTSTEP_EVERY_MOVES = 4  # DAT_0041a238 counts 0..3; sound when it was 3
LEADER_STOP_OFFSET_X = 0x1B  # step 6 c0 alone to stopX + 0x1b
CARRY_STOP_OFFSET_X = 0x50  # step 6 group to stopX + 0x50
MARCH_OFFSETS_X = (0, 0xD, 0x1B, 0x29, 0x37)
RALPH_ANIM_CARRIED = 30
RALPH_CARRIED_X = 170.0  # float 0x416bd0
# Step 7: Ralph, the Nicelanders and the camera move together.
RALPH_CARRY_STEP_X = 3.0  # double 0x416bc8
CAMERA_CARRY_STEP_X = -3
THROW_STOP_OFFSET_X = 0x65
THROW_VELOCITY = (2.0, -2.0)  # floats 0x416b40, 0x416b44
THROW_SOUND = 0x17
# Step 8
THROW_GRAVITY = 0.10000000149011612  # double 0x416bc0
THROW_CUT_X = 304.0  # float 0x416bbc; the cut happens once x > 304
FALL_START_Y = 32.0  # float 0x416bb8
GROUND_VIEW_SCROLL = (-0xA0, 0)
RALPH_ANIM_TUMBLING = 31
FALL_X = 0x130
FALL_SOUND = 0x13
# Step 9
FALL_SPEED = 3.7300000190734863  # double 0x416bb0
LANDING_Y = 317.0  # float 0x416bac; lands once y >= 317
RALPH_ANIM_LANDS = 32
LANDING_SOUND = 0x12
AFTER_LANDING_TICKS = 0x50  # phase 2 once the counter passes 80

# --- Phase 2, FUN_004044b0 / FUN_00404500 --------------------------------------
PHASE_2_TICKS = 0xB4  # the level advances once the counter passes 180
PHASE_2_LEVEL_FORMAT = "LEVEL {}"  # string 0x416324, level index + 1
PHASE_2_COMPLETE = "COMPLETE"  # string 0x416330
PHASE_2_COLOUR = 6
# Text cells follow Ralph's floats: row = trunc(y * 0.125 - k), column =
# -4 - trunc(x * -0.125) (doubles 0x416b38, 0x416b30, 0x416b20, 0x416b28).
PHASE_2_ROW_SCALE = 0.125
PHASE_2_LEVEL_ROW_OFFSET = 6.0
PHASE_2_COMPLETE_ROW_OFFSET = 4.0
PHASE_2_COLUMN_SCALE = -0.125
PHASE_2_COLUMN_BASE = -4
# Level indexes below 10 draw "LEVEL n" with FUN_0040f1d0, half a cell right.
PHASE_2_HALF_CELL_LEVEL_INDEX_LIMIT = 10
HALF_CELL_X = 4
GAME_END_LEVEL_INDEX = 0x26  # the 39th level ends the game instead of advancing

# --- Game end, FUN_0040af70 ---------------------------------------------------
GAME_END_GLYPHS = "11022012"  # string 0x41633c
GAME_END_FIRST_COLUMN = 0x1D  # DAT_00424294 restarts at 29 (FUN_0040a0f0)
GAME_END_ROW_STEPS = 0x29  # rows 0..40 per column; row 40 is never drawn
GAME_END_LAST_COLUMN = -0x28  # the screen ends when the column drops below -40
GAME_END_STEPS_PER_TICK = 4
GAME_END_COLOUR_COUNT = 7  # rand() % 7
TEXT_GRID_COLUMNS = 0x1E  # FUN_0040f350 draws columns < 30 and rows < 40
TEXT_GRID_ROWS = 0x28
TEXT_CELL_SIZE = 8
