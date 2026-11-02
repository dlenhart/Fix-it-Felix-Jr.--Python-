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

# [EXE] spawn timer (+0x82c): 0x5dc after a spawn (FUN_00407190), at a new game
# (FUN_004076e0) and at every level start (FUN_004089b0).
NICELANDER_SPAWN_TICKS = 1500
# [EXE] FUN_004084c0: the countdown ran out with fewer than 5 broken windows.
NICELANDER_REARM_TICKS = 600
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
        screen.blit(frame, (camera.to_screen_x(node_x - origin_x),
                            camera.to_screen_y(node_y) - origin_y))
        # FUN_00407190 links the pie after the Nicelander at the same depth: drawn in front.
        if self.pie is not None:
            self.pie.draw(screen, sprites, building, camera, palette)


class NicelanderDirector:
    """Spawns at most one Nicelander at a time on the exe's catch-up timer."""

    def __init__(self, rng: random.Random):
        self._rng = rng
        # The director is built per level, so this is the level-start value too.
        self._spawn_timer_ticks = NICELANDER_SPAWN_TICKS
        self.nicelander: Nicelander | None = None

    def tick(self, building: Building, felix: Felix, is_ralph_patrolling: bool,
             sound=None) -> bool:
        """Advance one tick. Returns True on the tick Felix collects the pie.

        [EXE] FUN_004084c0 runs the spawn timer and FUN_00407190 only while
        Ralph walks or pounds (state 0/1) and Felix is not in his hit sequence
        (state 10). A Nicelander already out keeps rising and its pie stays
        collectable (FUN_004070f0 runs every tick).
        """
        if self.nicelander is not None:
            return self._tick_nicelander(building, felix, sound)
        if not is_ralph_patrolling or felix.is_in_hit_sequence:
            return False
        if self._spawn_timer_ticks == 0:
            self._try_spawn(building, felix)
            return False
        # [EXE] FUN_004084c0: the broken-window minimum is only checked as the
        # countdown runs out; at 0, FUN_00407190 tries every tick until it spawns.
        self._spawn_timer_ticks -= 1
        if self._spawn_timer_ticks < 1 and building.broken_count < NICELANDER_MIN_BROKEN:
            self._spawn_timer_ticks = NICELANDER_REARM_TICKS
        return False

    def on_window_fixed(self, cell: WindowCell) -> None:
        """Fixing the window sends its Nicelander and pie away [ASSUMED]."""
        if self.nicelander is None or self.nicelander.cell is not cell:
            return
        self.nicelander = None

    def clear(self) -> None:
        """Section clear: remove any Nicelander and pie; the timer carries on.

        [EXE] FUN_00409ac0 clears the Nicelander-out flag (+0x7c2) but leaves the
        timer, which then counts down from where it stood.
        """
        self.nicelander = None

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
        return True

    def _try_spawn(self, building: Building, felix: Felix) -> None:
        candidates = self._candidate_cells(building, felix)
        if not candidates:
            return  # [EXE] FUN_00407190 returns; the timer stays 0
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
