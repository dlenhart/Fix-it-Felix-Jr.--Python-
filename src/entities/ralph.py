import random
from dataclasses import dataclass, field
from enum import Enum, auto

from constants import (
    BRICK_SPAWN_DROP, BRICK_SPAWN_SPREAD,
    RALPH_CLIMB_DAMAGE_CHANCE, RALPH_CLIMB_DAMAGE_INTERVAL_TICKS, RALPH_CLIMB_SPEED,
    RALPH_CYCLES_PER_DROP, RALPH_DROP_DELAY_TICKS,
    RALPH_PATROL_CENTER_X, RALPH_PATROL_SIDE_X,
    RALPH_POUND_BASE_TICKS, RALPH_POUND_DURATION_TICKS, RALPH_POUND_RANDOM_TICKS,
    RALPH_RAGE_BRICK_INTERVAL_TICKS, RALPH_RAGE_DURATION_TICKS, RALPH_RAGE_WINDUP_TICKS,
    RALPH_WALK_SPEED, SPRITE_FRAME_HOLD_TICKS,
)
from level_config import get_level_config

RALPH_SPRITE_FRAME_COUNT = 2


class RalphState(Enum):
    WALK = auto()
    POUND = auto()
    SECTION_POSE = auto()
    CLIMB = auto()
    RAGE = auto()
    IDLE = auto()


@dataclass
class RalphEvents:
    """What happened during one Ralph tick, for the game scene to act on."""
    brick_spawns: list[tuple[float, float]] = field(default_factory=list)
    is_drop_hazard_requested: bool = False
    is_climb_finished: bool = False


class Ralph:
    """Ralph as the exe's state machine (0x40e1a4). x is center, y is feet, in world coordinates."""

    def __init__(self, rng: random.Random):
        self._rng = rng
        self.x: float = RALPH_PATROL_CENTER_X
        self.y: float = 0
        self.state = RalphState.IDLE
        self._anim_ticks = 0
        self._target_x: float = RALPH_PATROL_SIDE_X[0]
        self._next_side_index = 0
        self._pound_ticks = 0
        self._brick_countdown_ticks = 0
        self._completed_cycles = 0
        self._drop_timer_ticks = 0
        self._rage_ticks = 0
        self._climb_ticks = 0

    def place_on_ledge(self, building) -> None:
        """Stand at the patrol center on the section ledge and start patrolling."""
        self.x = RALPH_PATROL_CENTER_X
        self.y = building.ledge_y()
        self._begin_walk()

    def idle(self) -> None:
        self.state = RalphState.IDLE

    def start_rage(self) -> None:
        """Felix ate a pie. Ignored during the section pose and the climb."""
        if self.state in (RalphState.CLIMB, RalphState.SECTION_POSE):
            return
        self.state = RalphState.RAGE
        self._rage_ticks = 0

    def start_section_clear(self) -> None:
        """Pose until start_climb; the game scene times the pose."""
        self.state = RalphState.SECTION_POSE

    def start_climb(self, building, from_y: float, first_heavy_cell=None, sound=None) -> None:
        """Climb from from_y to the building's (already advanced) ledge."""
        self.state = RalphState.CLIMB
        self.y = from_y
        self._climb_ticks = 0
        if first_heavy_cell is not None:
            building.damage(first_heavy_cell, is_heavy=True, sound=sound)

    def tick(self, building, level: int, sound=None) -> RalphEvents:
        events = RalphEvents()
        self._anim_ticks += 1
        self._tick_drop_timer(level, events)
        if self.state == RalphState.WALK:
            self._tick_walk()
        elif self.state == RalphState.POUND:
            self._tick_pound(events)
        elif self.state == RalphState.RAGE:
            self._tick_rage(events)
        elif self.state == RalphState.CLIMB:
            self._tick_climb(building, events, sound)
        return events

    def _tick_drop_timer(self, level: int, events: RalphEvents) -> None:
        if self._drop_timer_ticks == 0:
            return
        self._drop_timer_ticks -= 1
        if self._drop_timer_ticks > 0:
            return
        # The exe runs the timer on every level; the level table decides if it matters.
        if get_level_config(level).drop_hazards > 0:
            events.is_drop_hazard_requested = True

    def _begin_walk(self) -> None:
        self.state = RalphState.WALK
        if self.x != RALPH_PATROL_CENTER_X:
            self._target_x = RALPH_PATROL_CENTER_X
            return
        self._target_x = RALPH_PATROL_SIDE_X[self._next_side_index]
        self._next_side_index = 1 - self._next_side_index

    def _begin_pound(self) -> None:
        self.state = RalphState.POUND
        self._pound_ticks = 0
        self._roll_brick_countdown()

    def _roll_brick_countdown(self) -> None:
        self._brick_countdown_ticks = (
            RALPH_POUND_BASE_TICKS + self._rng.randint(0, RALPH_POUND_RANDOM_TICKS - 1))

    def _spawn_brick(self) -> tuple[float, float]:
        offset = self._rng.randint(-BRICK_SPAWN_SPREAD, BRICK_SPAWN_SPREAD - 1)
        return (self.x + offset, self.y + BRICK_SPAWN_DROP)

    def _tick_walk(self) -> None:
        remaining = self._target_x - self.x
        if abs(remaining) > RALPH_WALK_SPEED:
            self.x += RALPH_WALK_SPEED if remaining > 0 else -RALPH_WALK_SPEED
            return
        self.x = self._target_x
        self._begin_pound()

    def _tick_pound(self, events: RalphEvents) -> None:
        self._pound_ticks += 1
        self._brick_countdown_ticks -= 1
        if self._brick_countdown_ticks == 0:
            events.brick_spawns.append(self._spawn_brick())
            self._roll_brick_countdown()
        if self._pound_ticks < RALPH_POUND_DURATION_TICKS:
            return
        self._completed_cycles += 1
        if self._completed_cycles % RALPH_CYCLES_PER_DROP == 0:
            self._drop_timer_ticks = RALPH_DROP_DELAY_TICKS
        self._begin_walk()

    def _tick_rage(self, events: RalphEvents) -> None:
        self._rage_ticks += 1
        rage_end_tick = RALPH_RAGE_WINDUP_TICKS + RALPH_RAGE_DURATION_TICKS
        if self._rage_ticks >= rage_end_tick:
            self._begin_walk()
            return
        ticks_since_windup = self._rage_ticks - RALPH_RAGE_WINDUP_TICKS
        if ticks_since_windup < 0:
            return
        if ticks_since_windup % RALPH_RAGE_BRICK_INTERVAL_TICKS == 0:
            events.brick_spawns.append(self._spawn_brick())

    def _tick_climb(self, building, events: RalphEvents, sound) -> None:
        self._climb_ticks += 1
        if self.x != RALPH_PATROL_CENTER_X:
            self._slide_toward_center()
        else:
            self.y = max(self.y - RALPH_CLIMB_SPEED, building.ledge_y())
        if self._climb_ticks % RALPH_CLIMB_DAMAGE_INTERVAL_TICKS == 0:
            self._maybe_damage_window(building, sound)
        is_at_ledge = self.x == RALPH_PATROL_CENTER_X and self.y <= building.ledge_y()
        if not is_at_ledge:
            return
        events.is_climb_finished = True
        self._next_side_index = 0  # a new section restarts the patrol at 72
        self._begin_walk()

    def _slide_toward_center(self) -> None:
        remaining = RALPH_PATROL_CENTER_X - self.x
        if abs(remaining) <= RALPH_CLIMB_SPEED:
            self.x = RALPH_PATROL_CENTER_X
            return
        self.x += RALPH_CLIMB_SPEED if remaining > 0 else -RALPH_CLIMB_SPEED

    def _maybe_damage_window(self, building, sound) -> None:
        if self._rng.random() >= RALPH_CLIMB_DAMAGE_CHANCE:
            return
        floor = building.floor_at_y(self.y)
        if floor is None or floor not in building.section_floors():
            return
        damageable_cells = [cell for cell in floor.cells if cell.is_damageable]
        if not damageable_cells:
            return
        building.damage(self._rng.choice(damageable_cells), is_heavy=False, sound=sound)

    def _sprite_name(self) -> str:
        if self.state in (RalphState.POUND, RalphState.RAGE):
            return "ralph_smash"
        if self.state == RalphState.CLIMB:
            return "ralph_climb"
        return "ralph_idle"

    def draw(self, screen, sprites, camera, palette, alpha=1.0):
        """Draw centered on x and bottom-aligned on y."""
        frame = (self._anim_ticks // SPRITE_FRAME_HOLD_TICKS) % RALPH_SPRITE_FRAME_COUNT
        sprite = sprites.get_sprite(self._sprite_name(), frame, palette)
        left = camera.to_screen_x(round(self.x - sprite.get_width() / 2), alpha)
        top = camera.to_screen_y(self.y, alpha) - sprite.get_height()
        screen.blit(sprite, (left, top))
