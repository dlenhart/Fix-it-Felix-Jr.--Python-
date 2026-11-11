"""A Nicelander rising into a smashed pane with a pie (spec section 7)."""
from __future__ import annotations

import pygame

from core.camera import Camera
from entities.pie import Pie
from exe_data.sprite_data import (
    NICELANDER_CHARACTER_COUNT, NICELANDER_HANDOFF_FRAME_INDEX, NICELANDER_ORIGIN,
    NICELANDER_RISE_FRAME_START_TICKS, nicelander_rise_frame_ids,
)
from graphics.sprite_sheet import SpriteSheet
from world.building import Building
from world.window_cell import WindowCell


class Nicelander:
    """A Nicelander rising into a smashed pane; hands over the pie at the handoff frame."""

    def __init__(self, cell: WindowCell, character: int):
        if not 0 <= character < NICELANDER_CHARACTER_COUNT:
            raise ValueError(f"unknown Nicelander character: {character}")
        self.cell = cell
        self.character = character
        self.pie: Pie | None = None
        self._age_ticks = 0

    @property
    def frame_index(self) -> int:
        """Current rise frame; the last frame holds forever (mode 2 clamps)."""
        reached = [index for index, start in enumerate(NICELANDER_RISE_FRAME_START_TICKS)
                   if self._age_ticks >= start]
        return reached[-1]

    def tick(self) -> None:
        self._age_ticks += 1
        if self.pie is not None:
            self.pie.tick()
            return
        if self.frame_index >= NICELANDER_HANDOFF_FRAME_INDEX:
            self.pie = Pie(self.cell)

    def draw(self, screen: pygame.Surface, sprites: SpriteSheet, building: Building,
             camera: Camera, palette: int) -> None:
        frame_id = nicelander_rise_frame_ids(self.character)[self.frame_index]
        frame = sprites.get_frame(frame_id, palette)
        node_x, node_y = building.nicelander_node(self.cell)
        origin_x, origin_y = NICELANDER_ORIGIN
        screen.blit(frame, (camera.to_screen_x(node_x - origin_x),
                            camera.to_screen_y(node_y) - origin_y))
        # FUN_00407190 links the pie after the Nicelander at the same depth: drawn in front.
        if self.pie is not None:
            self.pie.draw(screen, sprites, building, camera, palette)
