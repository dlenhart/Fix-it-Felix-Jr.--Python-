"""Level-scaled hazards: sill obstacles, birds and Ralph's drop-hazards (spec section 8)."""
from __future__ import annotations

import random

import pygame

from camera import Camera
from constants import RALPH_PATROL_CENTER_X
from entities.building import CENTER_COLUMN, Building, Floor, WindowCell
from entities.felix import Felix
from entities.ralph import Ralph
from exe_tables import SPRITE_FRAMES
from level_config import CellKind, LevelConfig
from sprite_data import (
    BIRD_FRAME_HOLD_TICKS, BIRD_FRAMES_LEFT, BIRD_FRAMES_RIGHT, DROP_HAZARD_FRAME,
    DROP_HAZARD_ORIGIN, SILL_OBSTACLE_FRAME, SILL_OBSTACLE_ORIGIN,
)
from sprite_sheet import SpriteSheet

HAZARD_FLOOR_COUNT = 3  # [EXE] FUN_004067d0 / FUN_00406e00 use the section's top 3 floors
SILL_OBSTACLES_MAX_PER_FLOOR = 2  # [EXE] FUN_00406e00

BIRD_SPEED = 0.5  # [EXE] FUN_00406bb0 px/tick
BIRD_WRAP_LEFT_X = -32  # [EXE] FUN_00406bb0 also the start x of a bird entering from the left
BIRD_WRAP_RIGHT_X = 272  # [EXE] FUN_00406bb0 also the start x of a flipped bird
BIRD_WIDTH, BIRD_HEIGHT = SPRITE_FRAMES[BIRD_FRAMES_RIGHT[0]][2:]  # [EXE] frame 0 is 24x16
# FUN_0040ed40 shows each frame for hold + 1 ticks.
BIRD_FRAME_DISPLAY_TICKS = BIRD_FRAME_HOLD_TICKS + 1
BIRD_CENTER_ABOVE_FLOOR_BOTTOM = 25  # [ASSUMED] puts the bird at the height of the window glass

DROP_HAZARD_FALL_SPEED = 1.9  # [EXE] FUN_004073f0 px/tick
# TODO: FUN_00409360 caps the hazards *spawned* this section (0x421834, reset per
# section) at the level's limit, plus 3 slots; this caps the live count instead.
DROP_HAZARD_MAX_LIVE = 3  # [EXE] FUN_00409360
# [EXE] FUN_004073f0, after Felix touches it: visibility toggles every 15 ticks
# (timer 0xf, count 4), four visible phases and three hidden, then it is gone.
DROP_HAZARD_BLINKS = 4
DROP_HAZARD_BLINK_HALF_PERIOD_TICKS = 15
DROP_HAZARD_BLINK_TICKS = (2 * DROP_HAZARD_BLINKS - 1) * DROP_HAZARD_BLINK_HALF_PERIOD_TICKS
DROP_HAZARD_SPAWN_DROP = 8  # [EXE] FUN_00409360 spawns at Ralph's y + 8
# [EXE] FUN_004073f0 touch test (0x416b20, 0x416c18): within 4 px across and 5 px
# up or down of the hazard's node, against Felix's own box.
DROP_HAZARD_HALF_WIDTH = 4
DROP_HAZARD_HALF_HEIGHT = 5
DROP_HAZARD_PLACEMENT_ATTEMPTS = 4  # [EXE] FUN_00409360 rerolls a taken floor up to 4 times
# [EXE] FUN_00409360: gaps 1 and 2 flank the center cell; when the section's bottom
# floor has the door there, those gaps only take floors 2 and 3.
DROP_HAZARD_DOOR_SIDE_GAPS = (1, 2)
DROP_HAZARD_DOOR_SIDE_FIRST_FLOOR = 2

OBSTACLE_WIDTH, OBSTACLE_HEIGHT = SPRITE_FRAMES[SILL_OBSTACLE_FRAME][2:]  # [EXE] frame 214 is 32x8


def sill_obstacle_rect(building: Building, cell: WindowCell) -> pygame.Rect:
    """World rect of a cell's sill obstacle frame, bounce included.

    The node is Building.sill_obstacle_node, and anim 91's origin (11, 5) is
    the slab art's bottom center, so on a pane window the art covers rows 31-36,
    resting on top of the ledge.
    """
    node_x, node_y = building.sill_obstacle_node(cell)
    origin_x, origin_y = SILL_OBSTACLE_ORIGIN
    return pygame.Rect(node_x - origin_x, node_y + cell.sill_obstacle_offset_y - origin_y,
                       OBSTACLE_WIDTH, OBSTACLE_HEIGHT)


def _hazard_floors(building: Building) -> list[Floor]:
    """The section's top three floors; the bottom floor is hazard-free."""
    return building.section_floors()[-HAZARD_FLOOR_COUNT:]


def place_sill_obstacles(building: Building, count: int, rng: random.Random) -> None:
    """Set has_sill_obstacle on random non-arched cells of the section's top 3 floors.

    At most two per floor (FUN_00406e00). Raises ValueError if count cannot fit.
    """
    floors = _hazard_floors(building)
    if count > SILL_OBSTACLES_MAX_PER_FLOOR * len(floors):
        raise ValueError(f"cannot place {count} sill obstacles")
    for _ in range(count):
        open_floors = [
            floor for floor in floors
            if sum(cell.has_sill_obstacle for cell in floor.cells) < SILL_OBSTACLES_MAX_PER_FLOOR
        ]
        floor = rng.choice(open_floors)
        open_cells = [cell for cell in floor.cells
                      if cell.kind != CellKind.ARCHED and not cell.has_sill_obstacle]
        rng.choice(open_cells).has_sill_obstacle = True


def clear_sill_obstacles(building: Building) -> None:
    """Remove every sill obstacle of the active section."""
    for floor in building.section_floors():
        for cell in floor.cells:
            cell.has_sill_obstacle = False


class Bird:
    """A bird crossing one floor, wrapping at the screen edges. x is its left edge."""

    def __init__(self, floor: Floor, is_from_right: bool):
        self.floor = floor
        self.is_from_right = is_from_right
        self.x = self._start_x
        self._previous_x = self.x
        self._age_ticks = 0

    @property
    def _start_x(self) -> float:
        return float(BIRD_WRAP_RIGHT_X if self.is_from_right else BIRD_WRAP_LEFT_X)

    def rect(self) -> pygame.Rect:
        top = self.floor.bottom_y - BIRD_CENTER_ABOVE_FLOOR_BOTTOM - BIRD_HEIGHT // 2
        return pygame.Rect(round(self.x), top, BIRD_WIDTH, BIRD_HEIGHT)

    def reset(self) -> None:
        """Back to the entry edge, as the exe's respawn does (FUN_00406db0)."""
        self.x = self._start_x
        self._previous_x = self.x

    def tick(self) -> None:
        self._previous_x = self.x
        self._age_ticks += 1
        self.x += -BIRD_SPEED if self.is_from_right else BIRD_SPEED
        if self.x > BIRD_WRAP_RIGHT_X:
            self.x = float(BIRD_WRAP_LEFT_X)
        elif self.x < BIRD_WRAP_LEFT_X:
            self.x = float(BIRD_WRAP_RIGHT_X)

    def draw(self, screen: pygame.Surface, sprites: SpriteSheet, camera: Camera,
             palette: int, alpha: float) -> None:
        frames = BIRD_FRAMES_LEFT if self.is_from_right else BIRD_FRAMES_RIGHT
        frame = sprites.get_frame(frames[(self._age_ticks // BIRD_FRAME_DISPLAY_TICKS) % len(frames)],
                                  palette)
        has_wrapped = abs(self.x - self._previous_x) > 1
        x = self.x if has_wrapped else self._previous_x + (self.x - self._previous_x) * alpha
        screen.blit(frame, (round(x), camera.to_screen_y(self.rect().top)))


class DropHazard:
    """A brick chunk Ralph drops between two windows: falls, waits, blinks away once it hit Felix.

    x and y are the exe's node point (anim 98's origin), in world coordinates. It
    lands in the gap to the right of cell gap_index, at that cell's exe sill row.
    """

    def __init__(self, x: float, start_y: float, floor: Floor, gap_index: int, landing_y: float):
        self.x = float(x)
        self.y = float(start_y)
        self.floor = floor
        self.gap_index = gap_index
        self.landing_y = float(landing_y)
        self.is_blinking = False
        self.is_finished = False
        self._previous_y = self.y
        self._blink_ticks = 0

    @property
    def is_landed(self) -> bool:
        return self.y >= self.landing_y

    def rect(self) -> pygame.Rect:
        """The touch box of FUN_004073f0 around the node point."""
        return pygame.Rect(round(self.x) - DROP_HAZARD_HALF_WIDTH,
                           round(self.y) - DROP_HAZARD_HALF_HEIGHT,
                           2 * DROP_HAZARD_HALF_WIDTH, 2 * DROP_HAZARD_HALF_HEIGHT)

    def start_blinking(self) -> None:
        self.is_blinking = True
        self._blink_ticks = 0

    def tick(self) -> None:
        self._previous_y = self.y
        if self.is_blinking:
            self._blink_ticks += 1
            if self._blink_ticks >= DROP_HAZARD_BLINK_TICKS:
                self.is_finished = True
            return
        self.y = min(self.y + DROP_HAZARD_FALL_SPEED, self.landing_y)

    def draw(self, screen: pygame.Surface, sprites: SpriteSheet, camera: Camera,
             palette: int, alpha: float) -> None:
        if self.is_blinking and (self._blink_ticks // DROP_HAZARD_BLINK_HALF_PERIOD_TICKS) % 2 == 1:
            return
        y = self._previous_y + (self.y - self._previous_y) * alpha
        frame = sprites.get_frame(DROP_HAZARD_FRAME, palette)
        origin_x, origin_y = DROP_HAZARD_ORIGIN
        screen.blit(frame, (round(self.x) - origin_x, camera.to_screen_y(y, alpha) - origin_y))


def _make_drop_hazard(building: Building, floor: Floor, gap_index: int,
                      ralph_y: float) -> DropHazard:
    """FUN_00409360: x is the middle of the gap between the two cells' bounds."""
    left_cell, right_cell = floor.cells[gap_index], floor.cells[gap_index + 1]
    _, left_cell_right = building.sill_span_x(left_cell)
    right_cell_left, _ = building.sill_span_x(right_cell)
    gap_middle_x = (right_cell_left - left_cell_right) // 2 + left_cell_right
    return DropHazard(gap_middle_x, ralph_y + DROP_HAZARD_SPAWN_DROP, floor, gap_index,
                      landing_y=building.sill_y(left_cell))


class HazardField:
    """Owns the active section's birds and drop-hazards and draws its sill obstacles."""

    def __init__(self, rng: random.Random):
        self._rng = rng
        self._birds: list[Bird] = []
        self._drop_hazards: list[DropHazard] = []

    @property
    def birds(self) -> tuple[Bird, ...]:
        return tuple(self._birds)

    @property
    def drop_hazards(self) -> tuple[DropHazard, ...]:
        return tuple(self._drop_hazards)

    def start_section(self, building: Building, config: LevelConfig) -> None:
        """Place the active section's sill obstacles and birds (FUN_004067d0, FUN_00406e00)."""
        place_sill_obstacles(building, config.sill_obstacles, self._rng)
        floors = _hazard_floors(building)
        for _ in range(config.bird_pairs):
            from_right_floor, from_left_floor = self._rng.sample(floors, 2)
            self._birds.append(Bird(from_right_floor, is_from_right=True))
            self._birds.append(Bird(from_left_floor, is_from_right=False))

    def clear(self) -> None:
        """Section clear: birds and drop-hazards go. Obstacle flags are the caller's to clear."""
        self._birds.clear()
        self._drop_hazards.clear()

    def reset_birds(self) -> None:
        """Send every bird back to its entry edge; called when Felix respawns."""
        for bird in self._birds:
            bird.reset()

    def request_drop(self, ralph: Ralph, building: Building, config: LevelConfig) -> None:
        """Drop a hazard from Ralph into a gap between windows, if the level's limit allows.

        FUN_00409360: the gap follows Ralph's side, the floor is random, and a floor
        whose same gap already holds a hazard is rerolled; after 4 taken floors
        nothing drops.
        """
        if len(self._drop_hazards) >= min(config.drop_hazards, DROP_HAZARD_MAX_LIVE):
            return
        gap_index = self._choose_gap(ralph.x)
        floors = self._drop_floors(building, gap_index)
        for _ in range(DROP_HAZARD_PLACEMENT_ATTEMPTS):
            floor = self._rng.choice(floors)
            is_gap_taken = any(hazard.floor is floor and hazard.gap_index == gap_index
                               for hazard in self._drop_hazards)
            if is_gap_taken:
                continue
            self._drop_hazards.append(_make_drop_hazard(building, floor, gap_index, ralph.y))
            return

    def _choose_gap(self, ralph_x: float) -> int:
        """FUN_0040d970: the two gaps on Ralph's side, or the middle two when he is centered.

        The exe tests flag 0x421748, set when Ralph stops at x 0x78 (the center).
        """
        if ralph_x == RALPH_PATROL_CENTER_X:
            return 1 + self._rng.randrange(2)
        if ralph_x < RALPH_PATROL_CENTER_X:
            return self._rng.randrange(2)
        return 2 + self._rng.randrange(2)

    @staticmethod
    def _drop_floors(building: Building, gap_index: int) -> list[Floor]:
        floors = building.section_floors()
        has_door = floors[0].cells[CENTER_COLUMN].kind == CellKind.DOOR
        if gap_index in DROP_HAZARD_DOOR_SIDE_GAPS and has_door:
            return floors[DROP_HAZARD_DOOR_SIDE_FIRST_FLOOR:]
        return floors

    def is_threatening(self, hitbox: pygame.Rect) -> bool:
        """True if a drop-hazard is falling toward the hitbox or already sits on it.

        Birds are not counted: they move sideways and wrap, so no spot is safe from them.
        """
        for hazard in self._drop_hazards:
            if hazard.is_blinking:
                continue
            rect = hazard.rect()
            is_overlapping_horizontally = rect.left < hitbox.right and hitbox.left < rect.right
            is_reaching_hitbox = rect.bottom <= hitbox.bottom and hazard.landing_y > hitbox.top
            if is_overlapping_horizontally and is_reaching_hitbox:
                return True
        return False

    def tick(self, building: Building, felix: Felix, sound=None) -> bool:
        """Advance every hazard. Returns True if Felix was hit this tick."""
        for floor in building.section_floors():
            for cell in floor.cells:
                cell.tick_sill_obstacle()
        for bird in self._birds:
            bird.tick()
        for hazard in self._drop_hazards:
            hazard.tick()

        self._drop_hazards = [hazard for hazard in self._drop_hazards if not hazard.is_finished]
        return self._hit_felix_if_touched(felix, sound)

    def _hit_felix_if_touched(self, felix: Felix, sound) -> bool:
        # Touching does nothing while Felix is invulnerable or already in his hit sequence;
        # hit() refuses both, so a hazard is only spent by a hit that lands.
        felix_hitbox = felix.hitbox()
        for bird in self._birds:
            if bird.rect().colliderect(felix_hitbox) and felix.hit(sound):
                return True
        for hazard in self._drop_hazards:
            # [USER] harmless while falling; the exe's FUN_004073f0 tests the touch every tick.
            if hazard.is_blinking or not hazard.is_landed:
                continue
            if not hazard.rect().colliderect(felix_hitbox):
                continue
            if felix.hit(sound):
                hazard.start_blinking()
                return True
        return False

    def draw(self, screen: pygame.Surface, sprites: SpriteSheet, building: Building,
             camera: Camera, palette: int, alpha: float) -> None:
        self._draw_sill_obstacles(screen, sprites, building, camera, palette)
        for hazard in self._drop_hazards:
            hazard.draw(screen, sprites, camera, palette, alpha)
        for bird in self._birds:
            bird.draw(screen, sprites, camera, palette, alpha)

    @staticmethod
    def _draw_sill_obstacles(screen: pygame.Surface, sprites: SpriteSheet, building: Building,
                             camera: Camera, palette: int) -> None:
        frame = sprites.get_frame(SILL_OBSTACLE_FRAME, palette)
        for floor in building.section_floors():
            for cell in floor.cells:
                if not cell.has_sill_obstacle:
                    continue
                rect = sill_obstacle_rect(building, cell)
                screen.blit(frame, (rect.x, camera.to_screen_y(rect.y)))
