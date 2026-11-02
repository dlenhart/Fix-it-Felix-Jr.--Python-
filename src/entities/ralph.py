import random
from dataclasses import dataclass, field
from enum import Enum, auto

from constants import (
    BRICK_SPAWN_DROP, BRICK_SPAWN_SPREAD,
    RALPH_CLIMB_DAMAGE_CHANCE, RALPH_CLIMB_DAMAGE_INTERVAL_TICKS, RALPH_CLIMB_SPEED,
    RALPH_DROP_DELAY_TICKS, RALPH_POUND_ARRIVALS_PER_DROP,
    RALPH_PATROL_CENTER_X, RALPH_PATROL_SIDE_X,
    RALPH_POUND_BASE_TICKS, RALPH_POUND_RANDOM_TICKS,
    RALPH_RAGE_BRICK_INTERVAL_TICKS, RALPH_RAGE_DURATION_TICKS, RALPH_RAGE_WINDUP_TICKS,
    RALPH_WALK_SPEED,
)
from entities.sprite_node import SpriteNode
from level_config import get_level_config
from roof_data import Animation, AnimationFrame, AnimationMode


def _ralph_animation(mode: AnimationMode, origin_x: int, *frames: tuple[int, int]) -> Animation:
    return Animation(mode, tuple(AnimationFrame(frame_id, hold, origin_x, 71)
                                 for frame_id, hold in frames))


# [EXE] Ralph's entries in the animation table at 0x419800: (frame id, hold).
ANIM_STANDING = _ralph_animation(AnimationMode.STATIC, 24, (75, 0))  # 20: FUN_0040e3f0, last-section pose
ANIM_WALK = _ralph_animation(AnimationMode.LOOP, 33, (78, 8), (79, 8))  # 23: FUN_0040df6f
ANIM_POUND = _ralph_animation(  # 24: FUN_0040d870 on arrival
    AnimationMode.ONCE, 33, (80, 6), (81, 12), (82, 6), (83, 6), (84, 6), (85, 6),
    (82, 6), (83, 6), (84, 6), (85, 6))
ANIM_RAGE = _ralph_animation(AnimationMode.LOOP, 33, (86, 6), (87, 6))  # 25: FUN_0040dd90
ANIM_FISTS_UP = _ralph_animation(AnimationMode.LOOP, 33, (80, 6), (81, 6))  # 26: rage wind-up, pose, ledge
ANIM_CLIMB = _ralph_animation(AnimationMode.LOOP, 33, (88, 6), (89, 6))  # 27: FUN_0040dbb0

# [EXE] FUN_0040d970 / FUN_0040dd90 restart sound 0x10 when the node has just
# moved onto one of these frames.
SMASH_SOUND = 0x10
POUND_SMASH_FRAMES = (0x52, 0x54)
RAGE_SMASH_FRAMES = (0x56, 0x57)
# FUN_0040d970 leaves its wind-up phase (DAT_00421738 0 -> 1) once past frame 1.
POUND_LAST_WINDUP_FRAME_INDEX = 1


class DropHazardSchedule:
    """When Ralph's pounds request a drop hazard; lasts the whole game.

    [EXE] Only FUN_0040e3f0, at game start, resets DAT_00421740 / DAT_00421744,
    so the count carries across sections and levels, and an armed timer waits
    through walks, rages and level changes until the next pound.
    """

    def __init__(self) -> None:
        self._arrivals_until_drop = RALPH_POUND_ARRIVALS_PER_DROP
        self._timer_ticks = 0

    def on_pound_arrival(self) -> None:
        """FUN_0040d870: every 3rd arrival at a pound spot arms the 30-tick timer."""
        self._arrivals_until_drop -= 1
        if self._arrivals_until_drop != 0:
            return
        self._arrivals_until_drop = RALPH_POUND_ARRIVALS_PER_DROP
        self._timer_ticks = RALPH_DROP_DELAY_TICKS

    def tick_pound(self) -> bool:
        """FUN_0040d970's pound phase: count the timer down; True when it runs out."""
        if self._timer_ticks == 0:
            return False
        self._timer_ticks -= 1
        return self._timer_ticks == 0


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

    def __init__(self, rng: random.Random, drop_schedule: DropHazardSchedule | None = None):
        """drop_schedule is shared across levels by the game; a new one by default."""
        self._rng = rng
        self._drop_schedule = drop_schedule if drop_schedule is not None else DropHazardSchedule()
        self.x: float = RALPH_PATROL_CENTER_X
        self.y: float = 0
        self.state = RalphState.IDLE
        self._node = SpriteNode(ANIM_STANDING, is_visible=True)
        self._target_x: float = RALPH_PATROL_SIDE_X[0]
        # [EXE] +0xe28: the last walk ended at the center, so the next one heads out.
        self._was_last_arrival_center = True
        # [EXE] +0xe2e: heading out goes to 72 when False, 169 when True.
        self._is_next_side_right = False
        self._is_pound_windup_over = False
        self._brick_countdown_ticks = 0
        self._rage_ticks = 0
        self._climb_ticks = 0

    @property
    def frame_id(self) -> int:
        """The exe sprite frame Ralph shows now."""
        return self._node.frame.frame_id

    @property
    def is_patrolling(self) -> bool:
        """Walking or pounding: the exe's Ralph states 0 and 1 (+0x734)."""
        return self.state in (RalphState.WALK, RalphState.POUND)

    def place_on_ledge(self, building) -> None:
        """Stand at the patrol center on the section ledge and start patrolling.

        [EXE] FUN_00409610 puts him at x 0x78 with +0xe28 set, and the section's
        FUN_0040e220 clears +0xe2e, so every section's patrol starts toward 72.
        """
        self.x = RALPH_PATROL_CENTER_X
        self.y = building.ledge_y()
        self._was_last_arrival_center = True
        self._is_next_side_right = False
        self._begin_walk()

    def restart_patrol(self) -> None:
        """Felix respawned: FUN_0040e220 clears +0xe2e and restarts the walk (FUN_0040df60(0))."""
        self._is_next_side_right = False
        self._begin_walk()

    def idle(self) -> None:
        """Stand on the ledge waving his fists, as FUN_0040dbb0 leaves him after a climb."""
        if self.state == RalphState.IDLE:
            return
        self.state = RalphState.IDLE
        self._node.set_animation(ANIM_FISTS_UP)

    def start_rage(self) -> None:
        """Felix ate a pie. Ignored during the section pose and the climb."""
        if self.state in (RalphState.CLIMB, RalphState.SECTION_POSE):
            return
        self.state = RalphState.RAGE
        self._rage_ticks = 0
        self._node.set_animation(ANIM_FISTS_UP)  # FUN_0040e151

    def start_section_clear(self, is_last_section: bool = False) -> None:
        """Pose until start_climb; the game scene times the pose.

        [EXE] FUN_0040e090 (via FUN_0040e2b0) picks anim 20 when this is the
        level's last section (+0xef0 == 1), else anim 26.
        """
        self.state = RalphState.SECTION_POSE
        self._node.set_animation(ANIM_STANDING if is_last_section else ANIM_FISTS_UP)

    def start_climb(self, building, from_y: float, first_heavy_cell=None, sound=None) -> None:
        """Climb from from_y to the building's (already advanced) ledge."""
        self.state = RalphState.CLIMB
        self.y = from_y
        self._climb_ticks = 0
        self._node.set_animation(ANIM_CLIMB)
        if first_heavy_cell is not None:
            building.damage(first_heavy_cell, is_heavy=True, sound=sound)

    def tick(self, building, level: int, sound=None) -> RalphEvents:
        """Run the state handler, then step the animation (FUN_0040e310, then FUN_0040ed40)."""
        events = RalphEvents()
        if self.state == RalphState.WALK:
            self._tick_walk()
        elif self.state == RalphState.POUND:
            self._tick_pound(level, events, sound)
        elif self.state == RalphState.RAGE:
            self._tick_rage(events, sound)
        elif self.state == RalphState.CLIMB:
            self._tick_climb(building, events, sound)
        self._node.tick()
        return events

    def animate(self) -> None:
        """Step only the animation, for phases that hold Ralph's logic still.

        FUN_0040ed40 steps every node each tick whatever the game state.
        """
        self._node.tick()

    def _begin_walk(self) -> None:
        """FUN_0040df6f: back to the center, or out to the next side from the center."""
        self.state = RalphState.WALK
        self._node.set_animation(ANIM_WALK)
        if not self._was_last_arrival_center:
            self._target_x = RALPH_PATROL_CENTER_X
            return
        self._target_x = RALPH_PATROL_SIDE_X[1 if self._is_next_side_right else 0]
        self._is_next_side_right = not self._is_next_side_right

    def _begin_pound(self) -> None:
        """FUN_0040d870 on arrival: the first brick countdown is a flat 9 ticks."""
        self.state = RalphState.POUND
        self._was_last_arrival_center = self.x == RALPH_PATROL_CENTER_X
        self._node.set_animation(ANIM_POUND)
        self._is_pound_windup_over = False
        self._brick_countdown_ticks = RALPH_POUND_BASE_TICKS
        self._drop_schedule.on_pound_arrival()

    def _play_smash_sound(self, smash_frames: tuple[int, ...], sound) -> None:
        if sound is None or not self._node.has_frame_changed:
            return
        if self._node.frame.frame_id in smash_frames:
            sound.restart_sound_index(SMASH_SOUND)

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

    def _tick_pound(self, level: int, events: RalphEvents, sound) -> None:
        """FUN_0040d970: bricks and the drop timer only run once the wind-up is over."""
        self._play_smash_sound(POUND_SMASH_FRAMES, sound)
        if not self._is_pound_windup_over:
            self._is_pound_windup_over = self._node.frame_index > POUND_LAST_WINDUP_FRAME_INDEX
            return
        self._brick_countdown_ticks -= 1
        if self._brick_countdown_ticks == 0:
            events.brick_spawns.append(self._spawn_brick())
            self._roll_brick_countdown()
        # FUN_00409360 picks the hazard; levels without drop hazards never place one.
        if self._drop_schedule.tick_pound() and get_level_config(level).drop_hazards > 0:
            events.is_drop_hazard_requested = True
        if self._node.is_finished:
            self._begin_walk()

    def _tick_rage(self, events: RalphEvents, sound) -> None:
        self._play_smash_sound(RAGE_SMASH_FRAMES, sound)
        self._rage_ticks += 1
        rage_end_tick = RALPH_RAGE_WINDUP_TICKS + RALPH_RAGE_DURATION_TICKS
        if self._rage_ticks >= rage_end_tick:
            self._begin_walk()
            return
        ticks_since_windup = self._rage_ticks - RALPH_RAGE_WINDUP_TICKS
        if ticks_since_windup < 0:
            return
        if ticks_since_windup == 0:
            self._node.set_animation(ANIM_RAGE)  # FUN_0040dd90 after the wind-up
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
        self.idle()

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

    def draw(self, screen, sprites, camera, palette, alpha=1.0):
        """FUN_0040ee00: the frame's top-left at (x - origin x, y - origin y)."""
        frame = self._node.frame
        surface = sprites.get_frame(frame.frame_id, palette)
        screen.blit(surface, (camera.to_screen_x(self.x - frame.origin_x, alpha),
                              camera.to_screen_y(self.y - frame.origin_y, alpha)))
