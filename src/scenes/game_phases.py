"""Game phases for GameScene (State pattern): level start, play, section clear, level end.

Each phase owns its own timers. GameScene ticks the current phase, which
returns the next phase or None to stay.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from constants import GAME_WIDTH, GAME_HEIGHT, RALPH_SECTION_POSE_TICKS
from entities.felix import FelixState
from font_renderer import scale_text_to_fit
from level_config import STREET_Y

if TYPE_CHECKING:
    from scenes.game_scene import GameScene

READY_PAUSE_TICKS = 180  # [EXE] FUN_004086e0 ready countdown before play
SECTION_SCROLL_SPEED = 2.0  # [EXE] FUN_00408810 camera px/tick on section clear
LEVEL_END_HOLD_TICKS = 120  # [ASSUMED] placeholder hold until Task 11's roof sequence
DOOR_LOCAL_ROW = 0
DOOR_COLUMN = 2
SECTION_CLEAR_MESSAGE = "YOU FIXED IT!"  # [EXE string]


class GamePhase:
    """One phase of a level. Subclasses override tick and, optionally, draw_overlay."""

    def tick(self, game: GameScene) -> GamePhase | None:
        """Advance one tick. Return the phase that replaces this one, or None to stay."""
        raise NotImplementedError

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        """Draw phase text over the playfield. Default: nothing."""


def _enter_play(game: GameScene) -> GamePhase:
    """Hand off to play: Ralph leaves his idle pose and starts the patrol from the ledge."""
    game.ralph.place_on_ledge(game.building)
    return PlayPhase()


def _draw_centered_message(game: GameScene, screen: pygame.Surface, message: str) -> None:
    text = game.font.render_text(message, color_row=0)
    scaled = scale_text_to_fit(text, GAME_WIDTH - 16, preferred_scale=2.0)
    screen.blit(scaled, scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2)))


class LevelStartPhase(GamePhase):
    """Ralph climbs in from the street wrecking windows, then a LEVEL N ready pause."""

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
                first_heavy_cell=game.building.cell(DOOR_LOCAL_ROW, DOOR_COLUMN))
            self.has_climb_started = True

        if not self.is_ready_countdown:
            self._tick_climb(game)
            return None

        # Ralph stands idle and unticked through the countdown (Ruling 14).
        self.ready_ticks_remaining -= 1
        if self.ready_ticks_remaining > 0:
            return None
        return _enter_play(game)

    def _tick_climb(self, game: GameScene) -> None:
        events = game.ralph.tick(game.building, game.level)
        if not events.is_climb_finished:
            return
        game.ralph.idle()
        self.ready_ticks_remaining = READY_PAUSE_TICKS

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        if not self.is_ready_countdown:
            return
        _draw_centered_message(game, screen, f"LEVEL {game.level}")


class PlayPhase(GamePhase):
    """Normal play: Felix, Nicelanders, Ralph, then bricks, each tick."""

    def tick(self, game: GameScene) -> GamePhase | None:
        game.felix.tick(game.input_handler, game.building, game.sound,
                        is_spot_threatened=game.bricks.is_falling_toward)
        # Ruling 13: the game ends after the last death plays out, not on the fatal hit.
        if game.felix.is_game_over:
            game.end_game()
            return None
        # FUN_0040e1d0 freezes Ralph and every brick until the respawn unfreezes
        # them (FUN_0040e220); they stay drawn where they stopped.
        if game.felix.is_in_hit_sequence:
            return None

        if game.felix.last_fixed_points:
            game.nicelanders.on_window_fixed(
                game.building.cell(game.felix.local_row, game.felix.column))
        if game.nicelanders.tick(game.building, game.felix, game.sound):
            game.ralph.start_rage()

        events = game.ralph.tick(game.building, game.level)
        for brick_x, brick_y in events.brick_spawns:
            game.bricks.spawn(brick_x, brick_y)
        # events.is_drop_hazard_requested is ignored until Task 10 adds hazards.

        game.bricks.tick(game.building, game.felix, game.level, game.sound)

        if game.building.is_section_clear():
            return SectionClearPhase()
        return None


class SectionClearPhase(GamePhase):
    """Ralph poses, then climbs to the next section and the camera scrolls after him."""

    def __init__(self) -> None:
        self.has_started = False
        self.pose_ticks = 0
        self.is_climbing = False
        self.is_scrolling = False

    @property
    def is_posing(self) -> bool:
        return not self.is_climbing and not self.is_scrolling

    def tick(self, game: GameScene) -> GamePhase | None:
        if not self.has_started:
            self._start(game)

        if self.is_posing:
            # Ticked for the pose animation; Ralph throws nothing while posing.
            game.ralph.tick(game.building, game.level)
            return self._tick_pose(game)
        if self.is_climbing:
            self._tick_climb(game)
            return None
        # Ralph stands idle and unticked through the scroll (Ruling 14).
        return self._tick_scroll(game)

    def _tick_climb(self, game: GameScene) -> None:
        events = game.ralph.tick(game.building, game.level)
        if not events.is_climb_finished:
            return
        game.ralph.idle()
        self.is_climbing = False
        self.is_scrolling = True

    def _start(self, game: GameScene) -> None:
        self.has_started = True
        game.bricks.clear()
        game.bricks.reset_break_budget()
        game.nicelanders.clear()
        game.felix.state = FelixState.CELEBRATING
        game.ralph.start_section_clear()
        game.sound.play_sfx("section_clear")

    def _tick_pose(self, game: GameScene) -> GamePhase | None:
        self.pose_ticks += 1
        if self.pose_ticks < RALPH_SECTION_POSE_TICKS:
            return None
        if game.building.is_last_section:
            return LevelEndPhase()
        game.building.advance_section()
        game.ralph.start_climb(game.building, game.ralph.y)
        self.is_climbing = True
        return None

    def _tick_scroll(self, game: GameScene) -> GamePhase | None:
        target_scroll_y = game.building.scroll_target(game.building.section_index)
        has_arrived = game.camera.scroll_toward(target_scroll_y, SECTION_SCROLL_SPEED)
        if not has_arrived:
            return None
        game.felix.place_at(0, game.felix.column, game.building)
        return _enter_play(game)

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        if not self.is_posing:
            return
        _draw_centered_message(game, screen, SECTION_CLEAR_MESSAGE)


class LevelEndPhase(GamePhase):
    """Placeholder level end (Task 11 adds the roof sequence): hold, then the next level."""

    def __init__(self) -> None:
        self.hold_ticks = 0

    def tick(self, game: GameScene) -> GamePhase | None:
        self.hold_ticks += 1
        if self.hold_ticks < LEVEL_END_HOLD_TICKS:
            return None
        game.start_level(game.level + 1)
        # start_level already installed the next level's LevelStartPhase.
        return None

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        _draw_centered_message(game, screen, SECTION_CLEAR_MESSAGE)
