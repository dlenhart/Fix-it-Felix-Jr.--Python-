"""Ralph poses, climbs to the next section, and the camera scrolls after him (exe state 5)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from constants.display import SCREEN_CENTER
from constants.phases import SECTION_CLEAR_MESSAGE, SECTION_SCROLL_SPEED
from constants.ralph import RALPH_SECTION_CLIMB_WAIT_TICKS
from constants.sounds import SECTION_CLIMB_DONE_SOUND
from graphics.text_layout import draw_centered_text
from scenes.game.phases.game_phase import GamePhase

if TYPE_CHECKING:
    from scenes.game.game_scene import GameScene


class SectionClearPhase(GamePhase):
    """Ralph poses, then climbs to the next section and the camera scrolls after him.

    [EXE] Game state 5 (FUN_00408810). Its entry puts Ralph in the climb state
    (FUN_0040e0e1), which first waits 0x78 ticks in the pose FUN_0040e2b0 set on
    the fixing tick; then he climbs, sound 0x1d plays as he reaches the ledge,
    the camera scrolls 2 px/tick, and play resumes once it arrives.
    """

    def __init__(self) -> None:
        self.pose_ticks = 0
        self.is_climbing = False
        self.is_scrolling = False

    @property
    def is_posing(self) -> bool:
        return not self.is_climbing and not self.is_scrolling

    def tick(self, game: GameScene) -> GamePhase | None:
        if self.is_posing:
            # Ticked for the pose animation; Ralph throws nothing while posing.
            game.ralph.tick(game.building, game.session.level, game.sound)
            return self._tick_pose(game)
        if self.is_climbing:
            self._tick_climb(game)
            return None
        # Ralph's logic stands still through the scroll (Ruling 14); his animation steps.
        game.ralph.animate()
        return self._tick_scroll(game)

    def _tick_climb(self, game: GameScene) -> None:
        events = game.ralph.tick(game.building, game.session.level, game.sound)
        if not events.is_climb_finished:
            return
        game.ralph.idle()
        game.sound.play_sound_index(SECTION_CLIMB_DONE_SOUND)
        self.is_climbing = False
        self.is_scrolling = True

    def _tick_pose(self, game: GameScene) -> GamePhase | None:
        """Ralph's climb wait: the timer runs out on its 0x78th tick and he climbs the next."""
        self.pose_ticks += 1
        if self.pose_ticks < RALPH_SECTION_CLIMB_WAIT_TICKS:
            return None
        game.building.advance_section()
        game.ralph.start_climb(game.building, game.ralph.y, sound=game.sound)
        self.is_climbing = True
        return None

    def _tick_scroll(self, game: GameScene) -> GamePhase | None:
        target_scroll_y = game.building.scroll_target(game.building.section_index)
        has_arrived = game.camera.scroll_toward(target_scroll_y, SECTION_SCROLL_SPEED)
        if not has_arrived:
            return None
        # FUN_0040cac0 ends the pie's invulnerability as Felix enters the new section.
        game.felix.end_invulnerability()
        # TODO: FUN_0040cac0 starts a jump-up (FUN_0040bea0, sound 0xf) from the new
        # section's floor point (floor +0x2a8 - 1, +0x2ac, filled indirectly; not
        # decoded) and play resumes once he lands; we place him on row 0 at once.
        game.felix.place_at(0, game.felix.column, game.building)
        return game.enter_play()

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        if not self.is_posing:
            return
        draw_centered_text(screen, game.font, SECTION_CLEAR_MESSAGE, SCREEN_CENTER,
                           preferred_scale=2.0)
