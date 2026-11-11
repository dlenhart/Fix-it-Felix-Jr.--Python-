"""Spawns Nicelanders on the exe's catch-up timer (FUN_004084c0, FUN_00407190)."""

from __future__ import annotations

import random

import pygame

from audio.sound_sink import SILENT_SOUND, SoundSink
from constants.building import PANE_SMASHED
from constants.nicelanders import (
    NICELANDER_EXCLUDED_KINDS, NICELANDER_MAX_CANDIDATES, NICELANDER_MIN_BROKEN,
    NICELANDER_REARM_TICKS, NICELANDER_SPAWN_TICKS,
)
from core.camera import Camera
from entities.felix import Felix
from entities.nicelander import Nicelander
from exe_data.sprite_data import NICELANDER_CHARACTER_COUNT
from graphics.sprite_sheet import SpriteSheet
from world.building import Building
from world.window_cell import WindowCell


class NicelanderDirector:
    """Spawns at most one Nicelander at a time on the exe's catch-up timer."""

    def __init__(self, rng: random.Random):
        self._rng = rng
        # The director is built per level, so this is the level-start value too.
        self._spawn_timer_ticks = NICELANDER_SPAWN_TICKS
        self.nicelander: Nicelander | None = None

    def tick(self, building: Building, felix: Felix, is_ralph_patrolling: bool,
             sound: SoundSink = SILENT_SOUND) -> bool:
        """Advance one tick. Returns True on the tick Felix collects the pie.

        [EXE] FUN_004084c0 runs the spawn timer and FUN_00407190 only while
        Ralph walks or pounds (state 0/1) and Felix is not in his hit sequence
        (state 10); the gate below mirrors that for callers that tick the director
        during a hit. Within PlayPhase the hit freeze returns before this runs, so an
        existing Nicelander is held too ([ASSUMED]: FUN_004070f0 not decoded for this).
        Outside a hit, a Nicelander already out keeps rising and its pie stays
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
        self.nicelander = Nicelander(cell, self._rng.randrange(NICELANDER_CHARACTER_COUNT))
        self._spawn_timer_ticks = NICELANDER_SPAWN_TICKS

    @staticmethod
    def _candidate_cells(building: Building, felix: Felix) -> list[WindowCell]:
        """First 3 eligible cells scanning the section bottom to top, left to right.

        [ASSUMED] Scan order: the exe's FUN_00407190 walks the floor pointers down from
        0x4217f4 and may scan top to bottom; the floor array order is not decoded.
        """
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
