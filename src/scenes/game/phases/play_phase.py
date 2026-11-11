"""Normal play, and the section clear it hands off to."""
from __future__ import annotations

from typing import TYPE_CHECKING

from constants.sounds import BONUS_LIFE_SOUND, SECTION_CLEAR_JINGLE
from entities.felix_state import FelixState
from entities.sill_obstacles import clear_sill_obstacles
from scenes.game.phases.game_phase import GamePhase
from scenes.game.phases.level_end_phase import LevelEndPhase
from scenes.game.phases.section_clear_phase import SectionClearPhase
from scenes.game.play_tick_pipeline import PlayTickPipeline

if TYPE_CHECKING:
    from entities.events import FelixEvents
    from scenes.game.game_scene import GameScene


class PlayPhase(GamePhase):
    """Normal play: Felix, Nicelanders, Ralph, then bricks and hazards, each tick."""

    def __init__(self) -> None:
        self._play_tick = _SectionPlayTick()

    def tick(self, game: GameScene) -> GamePhase | None:
        return self._play_tick.run(game)


class _SectionPlayTick(PlayTickPipeline):
    """The play tick with the section-clear check and the Nicelanders after Felix."""

    def after_felix(self, game: GameScene, felix_events: FelixEvents) -> GamePhase | None:
        # FUN_0040bc80 clears the section on the fixing tick itself, inside Felix's
        # handler, so nothing can hit him later in that tick.
        if game.building.is_section_clear():
            if game.building.is_last_section:
                return LevelEndPhase()
            _clear_section(game)
            return SectionClearPhase()

        if felix_events.fixed_cell is not None:
            game.nicelanders.on_window_fixed(felix_events.fixed_cell)
        if game.nicelanders.tick(game.building, game.felix,
                                 game.ralph.is_patrolling, game.sound):
            game.ralph.start_rage()
        return None


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
    game.sound.stop_sound_index(BONUS_LIFE_SOUND)
    game.sound.play_music_index(SECTION_CLEAR_JINGLE, is_looping=False)
