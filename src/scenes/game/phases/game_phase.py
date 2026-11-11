"""The GamePhase interface (State pattern) for GameScene.

Each phase owns its own timers. GameScene ticks the current phase, which
returns the next phase or None to stay.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from scenes.game.game_scene import GameScene


class GamePhase:
    """One phase of a level. Subclasses override tick and, optionally, draw_overlay."""

    def tick(self, game: GameScene) -> GamePhase | None:
        """Advance one tick. Return the phase that replaces this one, or None to stay."""
        raise NotImplementedError

    def draw_world(self, game: GameScene, screen: pygame.Surface, alpha: float) -> None:
        """Draw the playfield under the HUD. Default: the building and every play entity."""
        game.draw_play_world(screen, alpha)

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        """Draw phase text over the playfield. Default: nothing."""
