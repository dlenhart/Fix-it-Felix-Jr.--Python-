"""Front-end screens: title, intro cutscene and game over."""

from constants.timing import seconds_to_ticks

TITLE_BLINK_TICKS = seconds_to_ticks(0.5)
GAME_OVER_TICKS = seconds_to_ticks(3.0)

CUTSCENE_STEPS = (
    {"duration_ticks": seconds_to_ticks(2.0), "text": "", "sprite": "building_exterior"},
    {"duration_ticks": seconds_to_ticks(2.5), "text": "HEY. YOU MOVED MY STUMP!", "sprite": "ralph_cutscene_idle"},
    {"duration_ticks": seconds_to_ticks(2.5), "text": "I'M GONNA WRECK IT!", "sprite": "ralph_cutscene_smash"},
    {"duration_ticks": seconds_to_ticks(2.0), "text": "FIX IT FELIX!", "sprite": None},
    {"duration_ticks": seconds_to_ticks(2.0), "text": "I CAN FIX IT!", "sprite": None},
)
