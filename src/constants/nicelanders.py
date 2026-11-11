"""Nicelander spawning (FUN_004084c0, FUN_00407190)."""

from world.level_types import CellKind

# [EXE] spawn timer (+0x82c): 0x5dc after a spawn (FUN_00407190), at a new game
# (FUN_004076e0) and at every level start (FUN_004089b0).
NICELANDER_SPAWN_TICKS = 1500
# [EXE] FUN_004084c0: the countdown ran out with fewer than 5 broken windows.
NICELANDER_REARM_TICKS = 600
NICELANDER_MIN_BROKEN = 5  # [EXE] FUN_004084c0
NICELANDER_MAX_CANDIDATES = 3  # [EXE] FUN_004084c0
NICELANDER_EXCLUDED_KINDS = (CellKind.DOOR, CellKind.ARCHED)  # [EXE]
