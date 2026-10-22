"""Level-scaled hazards: sill obstacles, birds and Ralph's drop-hazards (spec section 8)."""
from __future__ import annotations

import random

import pygame

from camera import Camera
from entities.building import Building, Floor, WindowCell
from entities.felix import Felix
from entities.ralph import Ralph
from exe_tables import SPRITE_FRAMES
from level_config import CellKind, LevelConfig
from sprite_data import (
    BIRD_FRAME_HOLD_TICKS, BIRD_FRAMES_LEFT, BIRD_FRAMES_RIGHT, SILL_OBSTACLE_FRAME,
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
DROP_HAZARD_MAX_LIVE = 3  # [EXE] FUN_00409360
DROP_HAZARD_BLINKS = 4  # [EXE] FUN_004073f0 blinks after Felix touches it
DROP_HAZARD_BLINK_HALF_PERIOD_TICKS = 4  # [ASSUMED] matches the brick and Felix blink rhythm
DROP_HAZARD_SPAWN_DROP = 8  # [EXE] FUN_00409360 spawns at Ralph's y + 8

OBSTACLE_WIDTH, OBSTACLE_HEIGHT = SPRITE_FRAMES[SILL_OBSTACLE_FRAME][2:]  # [EXE] frame 214 is 32x8


def _obstacle_rect(center_x: float, bottom_y: float) -> pygame.Rect:
    return pygame.Rect(round(center_x) - OBSTACLE_WIDTH // 2, round(bottom_y) - OBSTACLE_HEIGHT,
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
    """A hazard Ralph drops onto a sill: falls, waits, then blinks away once it hit Felix."""

    def __init__(self, x: float, start_y: float, target_cell: WindowCell, landing_y: float):
        self.x = float(x)
        self.y = float(start_y)
        self.target_cell = target_cell
        self.landing_y = float(landing_y)
        self.is_blinking = False
        self.is_finished = False
        self._previous_y = self.y
        self._blink_ticks = 0

    @property
    def is_landed(self) -> bool:
        return self.y >= self.landing_y

    def rect(self) -> pygame.Rect:
        return _obstacle_rect(self.x, self.y)

    def start_blinking(self) -> None:
        self.is_blinking = True
        self._blink_ticks = 0

    def tick(self) -> None:
        self._previous_y = self.y
        if self.is_blinking:
            self._blink_ticks += 1
            if self._blink_ticks >= DROP_HAZARD_BLINKS * 2 * DROP_HAZARD_BLINK_HALF_PERIOD_TICKS:
                self.is_finished = True
            return
        self.y = min(self.y + DROP_HAZARD_FALL_SPEED, self.landing_y)

    def draw(self, screen: pygame.Surface, sprites: SpriteSheet, camera: Camera,
             palette: int, alpha: float) -> None:
        if self.is_blinking and (self._blink_ticks // DROP_HAZARD_BLINK_HALF_PERIOD_TICKS) % 2 == 1:
            return
        y = self._previous_y + (self.y - self._previous_y) * alpha
        # TODO: drop-hazard sprite unidentified (spec section 8); borrows the sill obstacle frame.
        frame = sprites.get_frame(SILL_OBSTACLE_FRAME, palette)
        screen.blit(frame, (round(self.x) - OBSTACLE_WIDTH // 2,
                            camera.to_screen_y(y, alpha) - OBSTACLE_HEIGHT))


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
        """Drop a hazard from Ralph onto a random floor, if the level's limit allows."""
        if len(self._drop_hazards) >= min(config.drop_hazards, DROP_HAZARD_MAX_LIVE):
            return
        floor = self._rng.choice(building.section_floors())
        target_cell = min(floor.cells, key=lambda cell: abs(cell.center_x - ralph.x))
        self._drop_hazards.append(DropHazard(
            target_cell.center_x, ralph.y + DROP_HAZARD_SPAWN_DROP, target_cell,
            landing_y=building.sill_y(target_cell)))

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
            if hazard.is_blinking or not hazard.rect().colliderect(felix_hitbox):
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
                # [ASSUMED] the 32x8 frame sits on the sill; the exe's "sill + 9" offset is
                # relative to its own sill y, which is not our measured one.
                rect = _obstacle_rect(cell.center_x, building.sill_y(cell))
                screen.blit(frame, (rect.x, camera.to_screen_y(rect.y)))
