"""One window slot on a floor: pane or door damage and the sill obstacle's bounce."""

import random

from constants.building import (
    PANE_DAMAGE_MAX, PANE_INTACT, PANE_SMASHED, SILL_OBSTACLE_BOUNCE_OFFSETS_Y,
    SILL_OBSTACLE_BOUNCE_STEP_TICKS, SILL_OBSTACLE_BOUNCE_TICKS,
)
from exe_data.exe_tables import BUILDING_PIECES
from exe_data.level_table import CELL_PIECE
from world.level_types import CellKind


class WindowCell:
    """One window slot on a floor, with pane or door damage state."""

    def __init__(self, kind: CellKind, column: int, x: int, floor_index: int):
        self.kind = kind
        self.column = column
        self.x = x
        self.width: int = BUILDING_PIECES[CELL_PIECE[kind]][2]
        self.floor_index = floor_index
        self.top_pane = PANE_INTACT
        self.bottom_pane = PANE_INTACT
        self.door_damage = PANE_INTACT
        self.has_sill_obstacle = False
        self._obstacle_bounce_ticks: int | None = None

    @property
    def is_damageable(self) -> bool:
        # Decorative, never damaged. [ASSUMED] (spec section 3, first rebuild)
        return self.kind != CellKind.ARCHED

    @property
    def is_broken(self) -> bool:
        if self.kind == CellKind.DOOR:
            return self.door_damage > PANE_INTACT
        if self.kind == CellKind.ARCHED:
            return False
        return self.top_pane > PANE_INTACT or self.bottom_pane > PANE_INTACT

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    def damage(self, is_heavy: bool, rng: random.Random) -> None:
        """Apply FUN_00409840: set one random pane (or the door) to a damage level.

        Light sets rng.randint(1, 5), which can lower an already worse pane (exe
        behavior). Heavy sets 5. Arched cells ignore damage.
        """
        if not self.is_damageable:
            return
        level = PANE_SMASHED if is_heavy else rng.randint(1, PANE_DAMAGE_MAX)
        if self.kind == CellKind.DOOR:
            self.door_damage = level
        elif rng.random() < 0.5:
            self.top_pane = level
        else:
            self.bottom_pane = level

    def fix(self) -> None:
        """Restore the whole window; one hammer swing fixes every pane (FUN_00409a70)."""
        self.top_pane = PANE_INTACT
        self.bottom_pane = PANE_INTACT
        self.door_damage = PANE_INTACT

    def bump_sill_obstacle(self) -> None:
        """Start the obstacle's bounce (FUN_004097d0); a bump mid-bounce restarts it."""
        self._obstacle_bounce_ticks = 0

    def tick_sill_obstacle(self) -> None:
        """Advance the obstacle's bounce by one tick (FUN_004070f0)."""
        if self._obstacle_bounce_ticks is None:
            return
        self._obstacle_bounce_ticks += 1
        if self._obstacle_bounce_ticks > SILL_OBSTACLE_BOUNCE_TICKS:
            self._obstacle_bounce_ticks = None

    @property
    def sill_obstacle_offset_y(self) -> int:
        """How far the bouncing obstacle is drawn above its resting y (0 at rest)."""
        if self._obstacle_bounce_ticks is None or self._obstacle_bounce_ticks == 0:
            return 0
        step = (self._obstacle_bounce_ticks - 1) // SILL_OBSTACLE_BOUNCE_STEP_TICKS
        return SILL_OBSTACLE_BOUNCE_OFFSETS_Y[step]
