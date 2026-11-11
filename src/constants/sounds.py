"""Sound and music: event names to exe sound files, and exe sound indices by meaning.

Every entry is [EXE]: the index the exe plays for that event (inline buffer
rewinds through DAT_0041b244, or FUN_0040f4a0 for music). Files are soundN.wav.
"""

SOUND_FILE_PREFIX = "sound"

# Effects played by name.
SOUND_MAP = {
    # FUN_0040d490 (brick) / FUN_00406bb0 (bird): the hazard hits a Felix who is not invulnerable.
    "felix_hit": "sound0",
    # FUN_0040b510: a hammer swing starts at a broken window.
    "hammer_swing": "sound1",
    # FUN_0040b5e0: Felix takes the pie (with "invulnerable_tune").
    "pie_pickup": "sound2",
    # FUN_0040d490: a brick hits an invulnerable Felix and bounces off.
    "brick_bounce": "sound3",
    # FUN_00409840: a window takes damage while intact.
    "window_break": "sound5",
    # FUN_004097d0: a jump up bumps a sill obstacle.
    "obstacle_bump": "sound6",
    # FUN_0040c3d0 cases 4/5 (FUN_0040bea0) and FUN_0040cac0: the jump up.
    "jump": "sound15",
    # FUN_0040c3d0 case 6 (FUN_0040c0d0): the drop down.
    "drop_down": "sound17",
    # FUN_004076e0: a new game starts.
    "new_game": "sound20",
    # FUN_0040b5e0: the pie's 8 s invulnerability tune.
    "invulnerable_tune": "sound24",
    # FUN_004063d0: the score crosses a multiple of 5000 (a bonus life).
    "bonus_life": "sound25",
}

# Music played by name.
MUSIC_MAP = {
    # FUN_00402abd / FUN_00401000: the intro (ESI = 7).
    "intro": "sound7",
    # FUN_00402258 / FUN_00402b94: the title and attract screens, played once.
    "title": "sound9",
}

# Indices played, stopped or restarted directly.
RALPH_SMASH_SOUND = 0x10  # [EXE] FUN_0040d970 / FUN_0040dd90 on a pound or rage smash frame
GAMEPLAY_MUSIC = 0xE  # [EXE] FUN_00408fc0 case 3: FUN_0040f4a0(1), ESI 0xe
# [EXE] FUN_0040ca00 / FUN_0040c940: a hit with no spare lives calls FUN_0040f4a0(0)
# with ESI 0x15, replacing the in-level music; 0x13 there is the animation id.
FINAL_HIT_MUSIC = 0x15
# [EXE] FUN_00409ac0: FUN_0040f4a0(0), ESI 0x16 (one-shot) on a section clear;
# FUN_004063d0 stops it when a bonus life is awarded.
SECTION_CLEAR_JINGLE = 0x16
INVULNERABLE_TUNE_SOUND = 0x18  # [EXE] sound 24; state 6 entry (FUN_00408fc0 case 6) stops it
BONUS_LIFE_SOUND = 0x19  # [EXE] sound 25; FUN_00409ac0 stops it on every section clear
SECTION_CLIMB_DONE_SOUND = 0x1D  # [EXE] FUN_00408810: Ralph reached the new ledge
