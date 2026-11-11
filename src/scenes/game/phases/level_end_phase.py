"""The last section is clear: play runs on through the exe's countdown, then the roof."""
from __future__ import annotations

from typing import TYPE_CHECKING

from constants.phases import LEVEL_END_COUNTDOWN_TICKS, SCORE_POPUP_DELAY_TICKS, SCORE_POPUP_RISE_PX
from constants.sounds import BONUS_LIFE_SOUND, SECTION_CLEAR_JINGLE
from scenes.game.phases.game_phase import GamePhase
from scenes.game.phases.roof_phase import RoofPhase
from scenes.game.play_tick_pipeline import PlayTickPipeline

if TYPE_CHECKING:
    from scenes.game.game_scene import GameScene


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
        self._play_tick = PlayTickPipeline()

    def tick(self, game: GameScene) -> GamePhase | None:
        if not self.has_started:
            self.has_started = True
            self._start(game)
        # The state 3 updates that still have something to do: Felix, Ralph, bricks, hazards.
        self._play_tick.run(game)
        if game.felix.is_game_over:
            # Unreachable with exe timings (the death takes longer than the wait), but
            # a finished death sequence always ends the game; the pipeline ended it.
            return None
        self._tick_score_popup(game.session.frame_counter)
        if self.is_popup_up:
            return None
        self.countdown_ticks -= 1
        if self.countdown_ticks >= 1:
            return None
        game.felix.cancel_hit_sequence()
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
        game.sound.stop_sound_index(BONUS_LIFE_SOUND)
        game.sound.play_music_index(SECTION_CLEAR_JINGLE, is_looping=False)

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
