"""Game phases for GameScene (State pattern): level start, play, section clear, level end.

The roof ending and the game-end screen live in scenes/roof_phases.py.

Each phase owns its own timers. GameScene ticks the current phase, which
returns the next phase or None to stay.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from constants import GAME_WIDTH, GAME_HEIGHT, RALPH_SECTION_CLIMB_WAIT_TICKS
from entities.felix import FelixState
from font_renderer import scale_text_to_fit
from entities.hazards import clear_sill_obstacles
from level_config import STREET_Y, get_level_config
from sprite_data import FONT_GLYPH_SIZE, font_row_for_exe_colour

if TYPE_CHECKING:
    from scenes.game_scene import GameScene

READY_PAUSE_TICKS = 180  # [EXE] FUN_004086e0 ready countdown before play
SECTION_SCROLL_SPEED = 2.0  # [EXE] FUN_00408810 camera px/tick on section clear
DOOR_LOCAL_ROW = 0
DOOR_COLUMN = 2
SECTION_CLEAR_MESSAGE = "YOU FIXED IT!"  # [EXE string]
# [EXE] FUN_00408760 draws sprintf("PLAYER %d READY", player index + 1) (string
# 0x416470) at column 8, row 0x13, colour 5 through FUN_0040f140.
READY_MESSAGE_FORMAT = "PLAYER {} READY"
READY_PLAYER_NUMBER = 1  # single player: DAT_00424240 is always 0
READY_MESSAGE_COLUMN = 8
READY_MESSAGE_ROW = 0x13
READY_MESSAGE_COLOUR = 5
# [EXE] FUN_00409a70 starts the fixed window's score popup with a 0x2f-tick
# delay; FUN_004063d0 counts it down in the same tick, after Felix's fix.
SCORE_POPUP_DELAY_TICKS = 0x2F
# [EXE] FUN_004063d0 raises the popup 1 px on ticks where the frame counter is
# odd, from sill - 8, and ends it once it was above sill - 0x28 (32 px of rise).
SCORE_POPUP_RISE_PX = 0x28 - 8
# [EXE] FUN_00409ac0 arms DAT_00424280 = 0x3c when the last section is clear;
# FUN_004084c0 counts it down while no score popup is up, then enters state 6.
LEVEL_END_COUNTDOWN_TICKS = 0x3C
SECTION_CLEAR_STOPPED_SOUND = 0x19  # [EXE] FUN_00409ac0 stops sound 25, the bonus-life sound
SECTION_CLIMB_DONE_SOUND = 0x1d  # [EXE] FUN_00408810: Ralph reached the new ledge
SECTION_CLEAR_MUSIC = 0x16  # [EXE] FUN_00409ac0: FUN_0040f4a0(0), ESI 0x16 (one-shot)


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


def draw_exe_text(game: GameScene, screen: pygame.Surface, text: str, column: int, row: int,
                  exe_colour: int, offset_x: int = 0) -> None:
    """Draw text the way FUN_0040f140 does: 8x8 glyphs from cell (column, row), camera-relative.

    Screen x = DAT_0041a298 + column * 8 (+ offset_x; FUN_0040f1d0 adds 4) and
    screen y = DAT_0041a248 + row * 8, so the text scrolls with the world.
    """
    surface = game.font.render_text(text, color_row=font_row_for_exe_colour(exe_colour))
    screen.blit(surface, (game.camera.to_screen_x(column * FONT_GLYPH_SIZE + offset_x),
                          game.camera.to_screen_y(row * FONT_GLYPH_SIZE)))


class FelixRespawnWatcher:
    """Spots the tick Felix leaves the hit sequence (FUN_0040c1a0's respawn).

    Detected as a transition because Felix owns the respawn and exposes no event for it.
    """

    def __init__(self) -> None:
        self._was_in_hit_sequence = False

    def has_respawned(self, felix) -> bool:
        is_in_hit_sequence = felix.is_in_hit_sequence
        has_respawned = self._was_in_hit_sequence and not is_in_hit_sequence
        self._was_in_hit_sequence = is_in_hit_sequence
        return has_respawned


def _tick_ralph(game: GameScene) -> None:
    """Tick Ralph and act on his events: bricks to spawn, a drop hazard to place."""
    events = game.ralph.tick(game.building, game.level, game.sound)
    for brick_x, brick_y in events.brick_spawns:
        game.bricks.spawn(brick_x, brick_y)
    if events.is_drop_hazard_requested:
        game.hazards.request_drop(game.ralph, game.building, get_level_config(game.level))


def _enter_play(game: GameScene) -> GamePhase:
    """Hand off to play: Ralph leaves his idle pose and starts the patrol from the ledge."""
    game.ralph.place_on_ledge(game.building)
    game.hazards.start_section(game.building, get_level_config(game.level))
    game.play_gameplay_music()
    return PlayPhase()


def _draw_centered_message(game: GameScene, screen: pygame.Surface, message: str) -> None:
    text = game.font.render_text(message, color_row=0)
    scaled = scale_text_to_fit(text, GAME_WIDTH - 16, preferred_scale=2.0)
    screen.blit(scaled, scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2)))


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
        return _enter_play(game)

    def _tick_climb(self, game: GameScene) -> None:
        events = game.ralph.tick(game.building, game.level, game.sound)
        if not events.is_climb_finished:
            return
        game.ralph.idle()
        self.ready_ticks_remaining = READY_PAUSE_TICKS

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        if not self.is_ready_countdown:
            return
        draw_exe_text(game, screen, READY_MESSAGE_FORMAT.format(READY_PLAYER_NUMBER),
                      READY_MESSAGE_COLUMN, READY_MESSAGE_ROW, READY_MESSAGE_COLOUR)


class PlayPhase(GamePhase):
    """Normal play: Felix, Nicelanders, Ralph, then bricks and hazards, each tick."""

    def __init__(self) -> None:
        self._respawn_watcher = FelixRespawnWatcher()

    def tick(self, game: GameScene) -> GamePhase | None:
        game.felix.tick(game.input_handler, game.building, game.sound,
                        is_spot_threatened=lambda hitbox: self._is_spot_threatened(game, hitbox))
        has_respawned = self._respawn_watcher.has_respawned(game.felix)
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
        if has_respawned:
            # FUN_0040c1a0 -> FUN_0040e220, before Ralph's handler runs this tick.
            game.ralph.restart_patrol()

        # FUN_0040bc80 clears the section on the fixing tick itself, inside Felix's
        # handler, so nothing can hit him later in that tick.
        if game.building.is_section_clear():
            if game.building.is_last_section:
                return LevelEndPhase()
            _clear_section(game)
            return SectionClearPhase()

        if game.felix.last_fixed_points:
            game.nicelanders.on_window_fixed(
                game.building.cell(game.felix.local_row, game.felix.column))
        if game.nicelanders.tick(game.building, game.felix,
                                 game.ralph.is_patrolling, game.sound):
            game.ralph.start_rage()

        _tick_ralph(game)

        game.bricks.tick(game.building, game.felix, game.level, game.sound)
        if has_respawned:
            # Before the tick: the bird that hit Felix is frozen on him and would hit again.
            game.hazards.reset_birds()
        game.hazards.tick(game.building, game.felix, game.sound)

        return None

    @staticmethod
    def _is_spot_threatened(game: GameScene, hitbox: pygame.Rect) -> bool:
        """Respawn predicate: a falling brick or drop-hazard is bearing down on the spot.

        Counting drop-hazards is [ASSUMED]: Ruling 21, neither the exe nor a user ruling.
        """
        return game.bricks.is_falling_toward(hitbox) or game.hazards.is_threatening(hitbox)


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
            game.ralph.tick(game.building, game.level, game.sound)
            return self._tick_pose(game)
        if self.is_climbing:
            self._tick_climb(game)
            return None
        # Ralph's logic stands still through the scroll (Ruling 14); his animation steps.
        game.ralph.animate()
        return self._tick_scroll(game)

    def _tick_climb(self, game: GameScene) -> None:
        events = game.ralph.tick(game.building, game.level, game.sound)
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
        return _enter_play(game)

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        if not self.is_posing:
            return
        _draw_centered_message(game, screen, SECTION_CLEAR_MESSAGE)


class LevelEndPhase(GamePhase):
    """The last section is clear: play goes on until the exe's countdown runs out, then the roof.

    [EXE] On the last section FUN_00409ac0 skips state 5 (no climb, no message)
    and arms a 0x3c-tick countdown. Play state 3 (FUN_004084c0) keeps running:
    Felix stays playable, Ralph poses (state 3, set by FUN_0040e2b0), the
    drop-hazards and sill obstacles stay live. FUN_004084c0 enters the roof
    (state 6) once the countdown runs out; it only counts while the last fixed
    window's score popup is gone (cell +0x88), so the wait is the popup's delay
    and rise plus the countdown. A hit during the wait plays out as in play,
    but the countdown does not wait for it: see Felix.cancel_hit_sequence.

    We have no score popup, so only its timing is modelled; the exe also adds
    the fix score when the popup appears.
    """

    def __init__(self) -> None:
        self.has_started = False
        # The fix tick already counted the popup delay down once.
        self.popup_delay_ticks = SCORE_POPUP_DELAY_TICKS - 1
        self.popup_rise_px = 0
        self.is_popup_up = True
        self.countdown_ticks = LEVEL_END_COUNTDOWN_TICKS
        self._respawn_watcher = FelixRespawnWatcher()

    def tick(self, game: GameScene) -> GamePhase | None:
        if not self.has_started:
            self.has_started = True
            self._start(game)
        self._tick_play(game, self._respawn_watcher)
        if game.felix.is_game_over:
            # Unreachable with exe timings (the death takes longer than the wait),
            # but a finished death sequence always ends the game.
            game.end_game()
            return None
        self._tick_score_popup(game.frame_counter)
        if self.is_popup_up:
            return None
        self.countdown_ticks -= 1
        if self.countdown_ticks >= 1:
            return None
        game.felix.cancel_hit_sequence()
        from scenes.roof_phases import RoofPhase
        return RoofPhase()

    @staticmethod
    def _start(game: GameScene) -> None:
        """FUN_00409ac0's last-section path, with FUN_0040e2b0 and FUN_00406b30 before it."""
        game.bricks.clear()
        game.bricks.reset_break_budget()
        game.hazards.clear_birds()
        # FUN_00409ac0 hides the pie and its Nicelander; FUN_004084c0 only spawns
        # Nicelanders while Ralph patrols (state 0/1), so none come back.
        game.nicelanders.clear()
        game.ralph.start_section_clear(is_last_section=True)
        # FUN_00409ac0 stops sound 0x19 (the bonus-life sound) and plays 0x16.
        game.sound.stop_sound_index(SECTION_CLEAR_STOPPED_SOUND)
        game.sound.play_music_index(SECTION_CLEAR_MUSIC, is_looping=False)

    @staticmethod
    def _tick_play(game: GameScene, respawn_watcher: FelixRespawnWatcher) -> None:
        """The state 3 updates that still have something to do: Felix, Ralph, bricks, hazards."""
        game.felix.tick(game.input_handler, game.building, game.sound,
                        is_spot_threatened=lambda hitbox: PlayPhase._is_spot_threatened(game, hitbox))
        has_respawned = respawn_watcher.has_respawned(game.felix)
        # FUN_0040e1d0 freezes Ralph and the bricks for the hit, as in PlayPhase.
        if game.felix.is_in_hit_sequence:
            return
        if has_respawned:
            # FUN_0040e220 restarts Ralph's walk even here (his pose is not state 6),
            # so he can patrol, pound and throw again before the roof.
            game.ralph.restart_patrol()
        _tick_ralph(game)
        game.bricks.tick(game.building, game.felix, game.level, game.sound)
        game.hazards.tick(game.building, game.felix, game.sound)

    def _tick_score_popup(self, frame_counter: int) -> None:
        if not self.is_popup_up:
            return
        if self.popup_delay_ticks > 0:
            self.popup_delay_ticks -= 1
            return
        previous_rise_px = self.popup_rise_px
        self.popup_rise_px += frame_counter & 1
        if previous_rise_px > SCORE_POPUP_RISE_PX:
            self.is_popup_up = False


def _clear_section(game: GameScene) -> None:
    """Section clear: empty the hazards, Felix celebrates, Ralph poses, the jingle plays."""
    game.bricks.clear()
    game.bricks.reset_break_budget()
    game.hazards.clear()
    clear_sill_obstacles(game.building)
    game.nicelanders.clear()
    game.felix.state = FelixState.CELEBRATING
    game.ralph.start_section_clear(is_last_section=game.building.is_last_section)
    # FUN_00409ac0 stops sound 0x19 (the bonus-life sound) on every clear,
    # then plays the jingle as music, replacing sound 14 until play resumes.
    game.sound.stop_sound_index(SECTION_CLEAR_STOPPED_SOUND)
    game.sound.play_music_index(SECTION_CLEAR_MUSIC, is_looping=False)
