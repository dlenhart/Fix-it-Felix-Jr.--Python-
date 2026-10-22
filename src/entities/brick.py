"""Falling bricks thrown by Ralph (spec section 6)."""
import random

import pygame

from camera import Camera
from constants import (
    BRICK_BLINK_TICKS, BRICK_BOUNCE_GRAVITY, BRICK_BOUNCE_TICKS, BRICK_BOUNCE_VX,
    BRICK_BOUNCE_VY, BRICK_FALL_SPEED, BRICK_MAX_LIVE, BRICK_WINDOW_BREAK_MIN_LEVEL,
    BRICK_WINDOW_BREAK_ODDS, BRICK_WINDOW_BREAKS_PER_SECTION, GROUND_Y,
)
from entities.building import Building
from entities.felix import Felix
from sprite_data import BRICK_FRAMES
from sprite_sheet import SpriteSheet

BRICK_WIDTH = 16
BRICK_HEIGHT = 24  # frame 5 (16x16) with frame 4 (16x8) stacked on top, [ASSUMED] stacking
BRICK_LOWER_FRAME_HEIGHT = 16
WINDOW_BREAK_ROLL = 99  # [EXE] FUN_0040d490 the winning value of the 1-in-200 roll


class Brick:
    """One brick. (x, y) is the center x and bottom y in world coordinates."""

    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
        self._previous_x = self.x
        self._previous_y = self.y
        self.is_bouncing = False
        self.is_active = True
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._bounce_ticks = 0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x) - BRICK_WIDTH // 2, round(self.y) - BRICK_HEIGHT,
                           BRICK_WIDTH, BRICK_HEIGHT)

    def start_bounce(self, rng: random.Random) -> None:
        self.is_bouncing = True
        self._velocity_x = BRICK_BOUNCE_VX if rng.random() < 0.5 else -BRICK_BOUNCE_VX
        self._velocity_y = BRICK_BOUNCE_VY
        self._bounce_ticks = 0

    def tick_fall(self) -> None:
        self._remember_position()
        self.y += BRICK_FALL_SPEED

    def tick_bounce(self) -> None:
        self._remember_position()
        self._velocity_y += BRICK_BOUNCE_GRAVITY
        self.x += self._velocity_x
        self.y += self._velocity_y
        self._bounce_ticks += 1
        if self._bounce_ticks >= BRICK_BOUNCE_TICKS:
            self.is_active = False

    def draw(self, screen, sprites: SpriteSheet, camera: Camera, palette, alpha: float) -> None:
        if self.is_bouncing and (self._bounce_ticks // BRICK_BLINK_TICKS) % 2 == 1:
            return
        x = self._previous_x + (self.x - self._previous_x) * alpha
        y = self._previous_y + (self.y - self._previous_y) * alpha
        left = round(x) - BRICK_WIDTH // 2
        bottom = camera.to_screen_y(y, alpha)
        lower_frame_id, upper_frame_id = BRICK_FRAMES
        lower = sprites.get_frame(lower_frame_id, palette)
        upper = sprites.get_frame(upper_frame_id, palette)
        screen.blit(lower, (left, bottom - lower.get_height()))
        screen.blit(upper, (left, bottom - lower.get_height() - upper.get_height()))

    def _remember_position(self) -> None:
        self._previous_x = self.x
        self._previous_y = self.y


class BrickField:
    """Owns every live brick and resolves their collisions each tick."""

    def __init__(self, rng: random.Random):
        self._rng = rng
        self._bricks: list[Brick] = []
        self._window_break_budget = BRICK_WINDOW_BREAKS_PER_SECTION

    @property
    def live_count(self) -> int:
        return len(self._bricks)

    def spawn(self, x: float, y: float) -> None:
        if len(self._bricks) >= BRICK_MAX_LIVE:
            return
        self._bricks.append(Brick(x, y))

    def clear(self) -> None:
        self._bricks.clear()

    def is_falling_toward(self, hitbox: pygame.Rect) -> bool:
        """True if a falling brick is above the hitbox's feet and overlaps it horizontally.

        Bouncing bricks and bricks already past the feet can't hit it. Deliberately
        conservative: a brick several floors up still counts, however long it needs.
        """
        for brick in self._bricks:
            if brick.is_bouncing:
                continue
            brick_rect = brick.rect()
            is_overlapping_horizontally = (brick_rect.left < hitbox.right
                                           and hitbox.left < brick_rect.right)
            if is_overlapping_horizontally and brick_rect.bottom <= hitbox.bottom:
                return True
        return False

    def reset_break_budget(self) -> None:
        self._window_break_budget = BRICK_WINDOW_BREAKS_PER_SECTION

    def tick(self, building: Building, felix: Felix, level: int, sound=None) -> bool:
        """Advance every brick. Returns True if Felix was hit this tick."""
        was_felix_hit = False
        for brick in self._bricks:
            if brick.is_bouncing:
                brick.tick_bounce()
                continue
            brick.tick_fall()
            if brick.rect().colliderect(felix.hitbox()):
                if felix.is_invulnerable:
                    brick.start_bounce(self._rng)
                    continue
                # The brick vanishes even if Felix is already in the hit sequence (ruling R3).
                was_felix_hit |= bool(felix.hit(sound))
                brick.is_active = False
                continue
            if self._try_break_window(brick, building, level, sound):
                brick.is_active = False
                continue
            if brick.y >= GROUND_Y:
                brick.start_bounce(self._rng)
        self._bricks = [brick for brick in self._bricks if brick.is_active]
        return was_felix_hit

    def draw(self, screen, sprites: SpriteSheet, camera: Camera, palette, alpha: float) -> None:
        for brick in self._bricks:
            brick.draw(screen, sprites, camera, palette, alpha)

    def _try_break_window(self, brick: Brick, building: Building, level: int, sound) -> bool:
        if level < BRICK_WINDOW_BREAK_MIN_LEVEL or self._window_break_budget <= 0:
            return False
        brick_rect = brick.rect()
        for floor in building.section_floors():
            for cell in floor.cells:
                if not cell.is_damageable or cell.is_broken:
                    continue
                if not brick_rect.colliderect(building.glass_rect(cell)):
                    continue
                if self._rng.randrange(BRICK_WINDOW_BREAK_ODDS) != WINDOW_BREAK_ROLL:
                    continue
                building.damage(cell, is_heavy=False, sound=sound)
                self._window_break_budget -= 1
                return True
        return False
