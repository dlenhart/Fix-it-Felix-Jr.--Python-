"""Game phases inside a level: the ready pause, section clears and the level end."""

READY_PAUSE_TICKS = 180  # [EXE] FUN_004086e0 ready countdown before play
SECTION_SCROLL_SPEED = 2.0  # [EXE] FUN_00408810 camera px/tick on section clear
SECTION_CLEAR_MESSAGE = "YOU FIXED IT!"  # [EXE string]
# [EXE] FUN_00408760 draws sprintf("PLAYER %d READY", player index + 1) (string
# 0x416470) at column 8, row 0x13, colour 5 through FUN_0040f140.
READY_MESSAGE_FORMAT = "PLAYER {} READY"
READY_PLAYER_NUMBER = 1  # single player: DAT_00424240 is always 0
READY_MESSAGE_COLUMN = 8
READY_MESSAGE_ROW = 0x13
READY_MESSAGE_COLOUR = 5
# [EXE] FUN_00409a70 starts the fixed window's score popup with a 0x2f-tick
# delay; FUN_004063d0 counts it down in the same tick, after Felix's fix.
SCORE_POPUP_DELAY_TICKS = 0x2F
# [EXE] FUN_004063d0 raises the popup 1 px on ticks where the frame counter is
# odd, from sill - 8, and ends it once it was above sill - 0x28 (32 px of rise).
SCORE_POPUP_RISE_PX = 0x28 - 8
# [EXE] FUN_00409ac0 arms DAT_00424280 = 0x3c when the last section is clear;
# FUN_004084c0 counts it down while no score popup is up, then enters state 6.
LEVEL_END_COUNTDOWN_TICKS = 0x3C
