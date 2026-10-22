"""The pie a Nicelander hands out (spec section 7)."""
import pygame

from camera import Camera
from entities.building import Building, WindowCell
from entities.felix import Felix
from sprite_data import PIE_FRAMES, PIE_FRAME_HOLD_TICKS
from sprite_sheet import SpriteSheet

# FUN_0040ed40 shows each frame for hold + 1 ticks.
PIE_FRAME_DISPLAY_TICKS = PIE_FRAME_HOLD_TICKS + 1


class Pie:
    """A pie sitting in one window's bottom pane until Felix stands there."""

    def __init__(self, cell: WindowCell):
        self.cell = cell
        self._age_ticks = 0

    def tick(self) -> None:
        self._age_ticks += 1

    def is_collected_by(self, felix: Felix, building: Building) -> bool:
        """True when Felix stands on the pie's cell, in any non-hit state."""
        if felix.is_in_hit_sequence:
            return False
        return building.cell(felix.local_row, felix.column) is self.cell

    def draw(self, screen: pygame.Surface, sprites: SpriteSheet, building: Building,
             camera: Camera, palette: int) -> None:
        frame_index = (self._age_ticks // PIE_FRAME_DISPLAY_TICKS) % len(PIE_FRAMES)
        frame = sprites.get_frame(PIE_FRAMES[frame_index], palette)
        pane = building.bottom_pane_rect(self.cell)
        # [ASSUMED] the 16x16 pie frame covers the pane; its origin (5, 15) in the
        # exe is relative to an anchor we don't model.
        screen.blit(frame, (pane.x, camera.to_screen_y(pane.y)))
