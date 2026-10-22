"""The pie a Nicelander hands out (spec section 7)."""
import pygame

from camera import Camera
from entities.building import Building, WindowCell
from entities.felix import Felix
from sprite_data import PIE_FRAMES, PIE_FRAME_HOLD_TICKS, PIE_ORIGIN
from sprite_sheet import SpriteSheet

# FUN_0040ed40 shows each frame for hold + 1 ticks.
PIE_FRAME_DISPLAY_TICKS = PIE_FRAME_HOLD_TICKS + 1


class Pie:
    """A pie sitting on one window's sill until Felix stands there."""

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
        # [USER] centered on the cell and resting on top of the sill ledge, on the
        # sill obstacle's line; where the exe puts the pie's node isn't decoded.
        node_x, node_y = building.sill_middle_x(self.cell), building.sill_y(self.cell)
        origin_x, origin_y = PIE_ORIGIN
        screen.blit(frame, (node_x - origin_x, camera.to_screen_y(node_y) - origin_y))
