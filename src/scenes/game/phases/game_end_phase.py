"""The game-end screen: FUN_0040af70's "11022012" glyph fill over the frozen roof."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

import constants.roof as roof
from scenes.game.phases.game_phase import GamePhase

if TYPE_CHECKING:
    from scenes.game.game_scene import GameScene
    from scenes.game.phases.roof_phase import RoofPhase


class GameEndPhase(GamePhase):
    """FUN_0040af70 with DAT_004242a8 set: the "11022012" screen over the frozen roof.

    Each tick writes 4 cells of a 30x40 text grid, down a column from row 0 to
    40 (row 40 is never drawn), starting at column 29 and moving left. Columns
    below 0 only count rows, a pause, until the column drops below -40.
    Nothing else ticks: the roof's last frame stays drawn underneath.
    """

    def __init__(self, roof_phase: RoofPhase) -> None:
        self.roof_phase = roof_phase
        self.column = roof.GAME_END_FIRST_COLUMN  # DAT_00424294
        self.row = 0  # DAT_00424298
        self.glyph_index = 0  # DAT_00424290
        self.cells: dict[tuple[int, int], tuple[str, int]] = {}
        self.is_finished = False

    def tick(self, game: GameScene) -> GamePhase | None:
        if self.is_finished:
            return None
        for _ in range(roof.GAME_END_STEPS_PER_TICK):
            if self.column >= 0:
                exe_colour = game.rng.randrange(roof.GAME_END_COLOUR_COUNT)
                self.cells[(self.column, self.row)] = (roof.GAME_END_GLYPHS[self.glyph_index],
                                                       exe_colour)
            self.glyph_index = (self.glyph_index + 1) % len(roof.GAME_END_GLYPHS)
            is_column_done = self.row >= roof.GAME_END_ROW_STEPS - 1
            self.row += 1
            if not is_column_done:
                continue
            self.column -= 1
            self.row = 0
            if self.column < roof.GAME_END_LAST_COLUMN:
                self.is_finished = True
                game.finish_game_end_screen()
                return None
        return None

    def draw_world(self, game: GameScene, screen: pygame.Surface, alpha: float) -> None:
        self.roof_phase.draw_world(game, screen, alpha)

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        """FUN_0040f2e0 draws the text grid over everything, HUD included."""
        for (column, row), (glyph, exe_colour) in self.cells.items():
            if column >= roof.TEXT_GRID_COLUMNS or row >= roof.TEXT_GRID_ROWS:
                continue
            cell = game.font.render_opaque_glyph_cell(glyph, exe_colour)
            screen.blit(cell, (column * roof.TEXT_CELL_SIZE, row * roof.TEXT_CELL_SIZE))
