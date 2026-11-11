"""Per-tick event records the entities hand back to the game phases."""

from __future__ import annotations

from dataclasses import dataclass, field

from world.window_cell import WindowCell


@dataclass
class RalphEvents:
    """What happened during one Ralph tick, for the game scene to act on."""
    brick_spawns: list[tuple[float, float]] = field(default_factory=list)
    is_drop_hazard_requested: bool = False
    is_climb_finished: bool = False


@dataclass
class FelixEvents:
    """What happened during one Felix tick, for the game phases to act on."""
    fixed_cell: WindowCell | None = None
    fixed_points: int = 0
    has_respawned: bool = False
