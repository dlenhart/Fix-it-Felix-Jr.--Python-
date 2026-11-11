"""Ralph climbs in from the street, then the PLAYER 1 READY pause."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from constants.building import STREET_Y
from constants.grid import DOOR_COLUMN, DOOR_LOCAL_ROW
from constants.phases import (
    READY_MESSAGE_COLOUR, READY_MESSAGE_COLUMN, READY_MESSAGE_FORMAT, READY_MESSAGE_ROW,
    READY_PAUSE_TICKS, READY_PLAYER_NUMBER,
)
from graphics.text_layout import draw_exe_text
from scenes.game.phases.game_phase import GamePhase

if TYPE_CHECKING:
    from scenes.game.game_scene import GameScene


class LevelStartPhase(GamePhase):
    """Ralph climbs in from the street wrecking windows, then the PLAYER 1 READY pause."""

    def __init__(self) -> None:
        self.has_climb_started = False
        self.ready_ticks_remaining: int | None = None

    @property
    def is_ready_countdown(self) -> bool:
        return self.ready_ticks_remaining is not None

    def tick(self, game: GameScene) -> GamePhase | None:
        if not self.has_climb_started:
            # The door takes the climb's first heavy hit [ASSUMED] (spec section 5).
            game.ralph.start_climb(
                game.building, STREET_Y,
                first_heavy_cell=game.building.cell(DOOR_LOCAL_ROW, DOOR_COLUMN),
                sound=game.sound)
            self.has_climb_started = True

        if not self.is_ready_countdown:
            self._tick_climb(game)
            return None

        # Ralph's logic stands still through the countdown (Ruling 14); his
        # animation still steps, as FUN_0040ed40 steps every node.
        game.ralph.animate()
        self.ready_ticks_remaining -= 1
        if self.ready_ticks_remaining > 0:
            return None
        return game.enter_play()

    def _tick_climb(self, game: GameScene) -> None:
        events = game.ralph.tick(game.building, game.session.level, game.sound)
        if not events.is_climb_finished:
            return
        game.ralph.idle()
        self.ready_ticks_remaining = READY_PAUSE_TICKS

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        if not self.is_ready_countdown:
            return
        message = READY_MESSAGE_FORMAT.format(READY_PLAYER_NUMBER)
        draw_exe_text(screen, game.font, game.camera, message,
                      READY_MESSAGE_COLUMN, READY_MESSAGE_ROW, READY_MESSAGE_COLOUR)
