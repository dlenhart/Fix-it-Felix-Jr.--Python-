"""The active section's birds and drop-hazards, and the sill obstacles' tick and draw."""

from __future__ import annotations

import random

import pygame

from audio.sound_sink import SILENT_SOUND, SoundSink
from constants.grid import CENTER_COLUMN
from constants.hazards import (
    DROP_HAZARD_DOOR_SIDE_FIRST_FLOOR, DROP_HAZARD_DOOR_SIDE_GAPS, DROP_HAZARD_MAX_LIVE,
    DROP_HAZARD_PLACEMENT_ATTEMPTS, DROP_HAZARD_SPAWN_DROP,
)
from constants.ralph import RALPH_PATROL_CENTER_X
from core.camera import Camera
from entities.bird import Bird
from entities.drop_hazard import DropHazard
from entities.felix import Felix
from entities.ralph import Ralph
from entities.sill_obstacles import hazard_floors, place_sill_obstacles, sill_obstacle_rect
from exe_data.sprite_data import SILL_OBSTACLE_FRAME
from graphics.sprite_sheet import SpriteSheet
from world.building import Building
from world.floor import Floor
from world.level_types import CellKind, LevelConfig


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
        floors = hazard_floors(building)
        for _ in range(config.bird_pairs):
            from_right_floor, from_left_floor = self._rng.sample(floors, 2)
            self._birds.append(Bird(from_right_floor, is_from_right=True))
            self._birds.append(Bird(from_left_floor, is_from_right=False))

    def clear(self) -> None:
        """Section clear: birds and drop-hazards go. Obstacle flags are the caller's to clear."""
        self._birds.clear()
        self._drop_hazards.clear()

    def clear_birds(self) -> None:
        """Last section clear: FUN_00406b30 frees the active section's birds; drop-hazards stay."""
        self._birds.clear()

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
        gap_index = self._choose_gap(ralph)
        floors = self._drop_floors(building, gap_index)
        for _ in range(DROP_HAZARD_PLACEMENT_ATTEMPTS):
            floor = self._rng.choice(floors)
            is_gap_taken = any(hazard.floor is floor and hazard.gap_index == gap_index
                               for hazard in self._drop_hazards)
            if is_gap_taken:
                continue
            self._drop_hazards.append(_make_drop_hazard(building, floor, gap_index, ralph.y))
            return

    def _choose_gap(self, ralph: Ralph) -> int:
        """FUN_0040d970: the two gaps on Ralph's side, or the middle two when he is centered.

        The exe tests flag 0x421748, set when Ralph stops at x 0x78 (the center).
        """
        if ralph.has_stopped_at_center:
            return 1 + self._rng.randrange(2)
        if ralph.x < RALPH_PATROL_CENTER_X:
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
        """True if a non-blinking drop-hazard overlaps the hitbox horizontally and will reach it.

        [ASSUMED] Counting drop-hazards in the respawn check is neither exe nor user
        ruling (Ruling 21).

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

    def tick(self, building: Building, felix: Felix, sound: SoundSink = SILENT_SOUND) -> bool:
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
                sound.play_sfx("felix_hit")  # FUN_00406bb0: sound 0
                return True
        # FUN_004073f0 plays no sound for a drop-hazard hit.
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
                screen.blit(frame, (camera.to_screen_x(rect.x), camera.to_screen_y(rect.y)))
