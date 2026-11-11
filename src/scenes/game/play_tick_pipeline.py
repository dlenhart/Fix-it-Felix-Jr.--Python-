"""The play-state tick shared by PlayPhase and LevelEndPhase (exe state 3, FUN_004084c0)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from entities.events import FelixEvents
from world.level_config import get_level_config

if TYPE_CHECKING:
    from scenes.game.game_scene import GameScene
    from scenes.game.phases.game_phase import GamePhase


class PlayTickPipeline:
    """One tick of play in the exe's order (Template Method).

    Felix, then the game-over and hit-freeze checks, the respawn's patrol
    restart, the after_felix hook, Ralph, the bricks and the hazards. Subclasses
    fill in after_felix; LevelEndPhase runs the base pipeline as is.
    """

    def run(self, game: GameScene) -> GamePhase | None:
        """Advance one play tick. Returns a phase only when after_felix asks for one."""
        felix_events = game.felix.tick(
            game.input_handler, game.building, game.sound,
            is_spot_threatened=lambda hitbox: is_spot_threatened(game, hitbox))
        # Ruling 13: the game ends after the last death plays out, not on the fatal hit.
        if game.felix.is_game_over:
            game.end_game()
            return None
        # FUN_0040e1d0 freezes Ralph and every brick until the respawn unfreezes
        # them (FUN_0040e220); they stay drawn where they stopped. This early return
        # also freezes birds, drop-hazards, the obstacle bounce (hazards per Ruling 20)
        # and an existing Nicelander ([ASSUMED]: FUN_004070f0 not decoded for this).
        if game.felix.is_in_hit_sequence:
            return None
        if felix_events.has_respawned:
            # FUN_0040c1a0 -> FUN_0040e220, before Ralph's handler runs this tick. It
            # restarts his walk even in the level-end wait (his pose is not state 6).
            game.ralph.restart_patrol()

        next_phase = self.after_felix(game, felix_events)
        if next_phase is not None:
            return next_phase

        tick_ralph(game)
        game.bricks.tick(game.building, game.felix, game.session.level, game.sound)
        if felix_events.has_respawned:
            # Before the tick: the bird that hit Felix is frozen on him and would hit again.
            game.hazards.reset_birds()
        game.hazards.tick(game.building, game.felix, game.sound)
        return None

    def after_felix(self, game: GameScene, felix_events: FelixEvents) -> GamePhase | None:
        """Hook between Felix's handler and Ralph's; return a phase to end the tick there."""
        return None


def tick_ralph(game: GameScene) -> None:
    """Tick Ralph and act on his events: bricks to spawn, a drop hazard to place."""
    events = game.ralph.tick(game.building, game.session.level, game.sound)
    for brick_x, brick_y in events.brick_spawns:
        game.bricks.spawn(brick_x, brick_y)
    if events.is_drop_hazard_requested:
        game.hazards.request_drop(game.ralph, game.building, get_level_config(game.session.level))


def is_spot_threatened(game: GameScene, hitbox: pygame.Rect) -> bool:
    """Respawn predicate: a falling brick or drop-hazard is bearing down on the spot.

    Counting drop-hazards is [ASSUMED]: Ruling 21, neither the exe nor a user ruling.
    """
    return game.bricks.is_falling_toward(hitbox) or game.hazards.is_threatening(hitbox)
