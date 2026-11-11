"""A brick chunk Ralph drops between two windows (FUN_004073f0)."""

import pygame

from constants.hazards import (
    DROP_HAZARD_BLINK_HALF_PERIOD_TICKS, DROP_HAZARD_BLINK_TICKS, DROP_HAZARD_FALL_SPEED,
    DROP_HAZARD_HALF_HEIGHT, DROP_HAZARD_HALF_WIDTH,
)
from core.camera import Camera
from exe_data.sprite_data import DROP_HAZARD_FRAME, DROP_HAZARD_ORIGIN
from graphics.sprite_sheet import SpriteSheet
from world.floor import Floor


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
        screen.blit(frame, (camera.to_screen_x(round(self.x) - origin_x, alpha),
                            camera.to_screen_y(y, alpha) - origin_y))
