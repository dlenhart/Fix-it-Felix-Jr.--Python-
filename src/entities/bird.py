"""A bird crossing one floor (FUN_00406bb0)."""

import pygame

from constants.hazards import (
    BIRD_CENTER_ABOVE_FLOOR_BOTTOM, BIRD_SPEED, BIRD_WRAP_LEFT_X, BIRD_WRAP_RIGHT_X,
)
from core.camera import Camera
from exe_data.sprite_data import (
    BIRD_FRAME_DISPLAY_TICKS, BIRD_FRAME_SIZE, BIRD_FRAMES_LEFT, BIRD_FRAMES_RIGHT,
)
from graphics.sprite_sheet import SpriteSheet
from world.floor import Floor


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
        width, height = BIRD_FRAME_SIZE
        top = self.floor.bottom_y - BIRD_CENTER_ABOVE_FLOOR_BOTTOM - height // 2
        return pygame.Rect(round(self.x), top, width, height)

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
        screen.blit(frame, (camera.to_screen_x(round(x)), camera.to_screen_y(self.rect().top)))
