"""What one game carries from level to level."""

from dataclasses import dataclass, field

from entities.drop_hazard_schedule import DropHazardSchedule


@dataclass
class GameSession:
    """Per-game state that survives GameScene.start_level, which rebuilds only the world.

    Felix also survives a level change: he carries the score and lives himself.
    """
    level: int
    # [EXE] DAT_0042427c: counts every game tick; the score popup and the
    # roof's "YOU FIXED IT!" colour cycle read its low bits.
    frame_counter: int = 0
    # [EXE] DAT_004242a6: 'N' was pressed; the game ends after the next roof.
    # TODO: the exe keeps this flag (and roof_footstep_counter) for the whole
    # program run, so a press on the title screen also counts; ours is per game.
    is_end_game_requested: bool = False
    # [EXE] DAT_00421740 / DAT_00421744: reset only at game start (FUN_0040e3f0).
    drop_hazard_schedule: DropHazardSchedule = field(default_factory=DropHazardSchedule)
    # [EXE] DAT_0041a238: the roof march's footstep counter is never reset.
    roof_footstep_counter: int = 0
