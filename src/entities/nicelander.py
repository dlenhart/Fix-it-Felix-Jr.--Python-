"""Nicelanders and the director that spawns them (spec section 7)."""
from __future__ import annotations

import random

import pygame

from camera import Camera
from entities.building import PANE_SMASHED, Building, CellKind, WindowCell
from entities.felix import Felix
from entities.pie import Pie
from sprite_data import (
    NICELANDER_CHARACTER_COUNT, NICELANDER_HANDOFF_FRAME_INDEX, NICELANDER_ORIGIN,
    NICELANDER_RISE_HOLD_TICKS, nicelander_rise_frame_ids,
)
from sprite_sheet import SpriteSheet

NICELANDER_SPAWN_TICKS = 1500  # [EXE] FUN_004084c0 timer after a spawn
NICELANDER_REARM_TICKS = 600  # [EXE] FUN_004084c0 re-arm when too few windows are broken
NICELANDER_MIN_BROKEN = 5  # [EXE] FUN_004084c0
NICELANDER_MAX_CANDIDATES = 3  # [EXE] FUN_004084c0
NICELANDER_CHARACTERS = NICELANDER_CHARACTER_COUNT  # [EXE] table 0x419e50
NICELANDER_EXCLUDED_KINDS = (CellKind.DOOR, CellKind.ARCHED)  # [EXE]


def _frame_start_ticks() -> tuple[int, ...]:
    """Tick at which each rise frame begins; FUN_0040ed40 shows a frame hold + 1 ticks."""
    start_ticks = []
    elapsed = 0
    for hold in NICELANDER_RISE_HOLD_TICKS:
        start_ticks.append(elapsed)
        elapsed += hold + 1
    return tuple(start_ticks)


FRAME_START_TICKS = _frame_start_ticks()


class Nicelander:
    """A Nicelander rising into a smashed pane; hands over the pie at the handoff frame."""

    def __init__(self, cell: WindowCell, character: int):
        if not 0 <= character < NICELANDER_CHARACTERS:
            raise ValueError(f"unknown Nicelander character: {character}")
        self.cell = cell
        self.character = character
        self.pie: Pie | None = None
        self._age_ticks = 0

    @property
    def frame_index(self) -> int:
        """Current rise frame; the last frame holds forever (mode 2 clamps)."""
        reached = [index for index, start in enumerate(FRAME_START_TICKS)
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
        screen.blit(frame, (node_x - origin_x, camera.to_screen_y(node_y) - origin_y))
        # FUN_00407190 links the pie after the Nicelander at the same depth: drawn in front.
        if self.pie is not None:
            self.pie.draw(screen, sprites, building, camera, palette)


class NicelanderDirector:
    """Spawns at most one Nicelander at a time on the exe's catch-up timer."""

    def __init__(self, rng: random.Random):
        self._rng = rng
        # [ASSUMED] starts at 0 so the first attempt is on the first play tick.
        self._spawn_timer_ticks = 0
        self.nicelander: Nicelander | None = None

    def tick(self, building: Building, felix: Felix, sound=None) -> bool:
        """Advance one tick. Returns True on the tick Felix collects the pie."""
        if self.nicelander is not None:
            return self._tick_nicelander(building, felix, sound)
        if self._spawn_timer_ticks > 0:
            self._spawn_timer_ticks -= 1
            return False
        self._try_spawn(building, felix)
        return False

    def on_window_fixed(self, cell: WindowCell) -> None:
        """Fixing the window sends its Nicelander and pie away [ASSUMED]."""
        if self.nicelander is None or self.nicelander.cell is not cell:
            return
        self.nicelander = None

    def clear(self) -> None:
        """Section clear: remove any Nicelander and pie and restart the timer [ASSUMED]."""
        self.nicelander = None
        self._spawn_timer_ticks = 0

    def draw(self, screen: pygame.Surface, sprites: SpriteSheet, building: Building,
             camera: Camera, palette: int) -> None:
        if self.nicelander is None:
            return
        self.nicelander.draw(screen, sprites, building, camera, palette)

    def _tick_nicelander(self, building: Building, felix: Felix, sound) -> bool:
        self.nicelander.tick()
        pie = self.nicelander.pie
        if pie is None or not pie.is_collected_by(felix, building):
            return False
        self.nicelander = None
        felix.activate_invulnerability(sound)
        if sound:
            sound.play_sfx("pie_pickup")
        return True

    def _try_spawn(self, building: Building, felix: Felix) -> None:
        candidates = self._candidate_cells(building, felix)
        if building.broken_count < NICELANDER_MIN_BROKEN or not candidates:
            # [ASSUMED] no candidate despite enough breaks also waits the re-arm time.
            self._spawn_timer_ticks = NICELANDER_REARM_TICKS
            return
        cell = self._rng.choice(candidates)
        self.nicelander = Nicelander(cell, self._rng.randrange(NICELANDER_CHARACTERS))
        self._spawn_timer_ticks = NICELANDER_SPAWN_TICKS

    @staticmethod
    def _candidate_cells(building: Building, felix: Felix) -> list[WindowCell]:
        """First 3 eligible cells scanning the section bottom to top, left to right."""
        felix_floor = building.section_floors()[felix.local_row]
        candidates: list[WindowCell] = []
        for floor in building.section_floors():
            if floor is felix_floor:
                continue
            for cell in floor.cells:
                if cell.kind in NICELANDER_EXCLUDED_KINDS or cell.bottom_pane != PANE_SMASHED:
                    continue
                candidates.append(cell)
        return candidates[:NICELANDER_MAX_CANDIDATES]
