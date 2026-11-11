"""One falling brick thrown by Ralph (spec section 6)."""
import random

import pygame

from constants.bricks import (
    BRICK_BLINK_TICKS, BRICK_BOUNCE_GRAVITY, BRICK_BOUNCE_TICKS, BRICK_BOUNCE_VX,
    BRICK_BOUNCE_VY, BRICK_FALL_SPEED, BRICK_HEIGHT, BRICK_WIDTH,
)
from core.camera import Camera
from exe_data.sprite_data import BRICK_FRAMES
from graphics.sprite_sheet import SpriteSheet


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
        left = camera.to_screen_x(round(x) - BRICK_WIDTH // 2, alpha)
        bottom = camera.to_screen_y(y, alpha)
        lower_frame_id, upper_frame_id = BRICK_FRAMES
        lower = sprites.get_frame(lower_frame_id, palette)
        upper = sprites.get_frame(upper_frame_id, palette)
        screen.blit(lower, (left, bottom - lower.get_height()))
        screen.blit(upper, (left, bottom - lower.get_height() - upper.get_height()))

    def _remember_position(self) -> None:
        self._previous_x = self.x
        self._previous_y = self.y
