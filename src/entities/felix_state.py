"""Felix's state machine states and the groups the game asks about."""

import enum


class FelixState(enum.Enum):
    IDLE = 0
    WALK_HORIZONTAL = 1
    JUMPING = 4
    JUMP_BUMPED = 7
    HAMMERING = 5
    HAMMER_EXTENDED = 6
    HIT_ANIM = 8
    HIT_FALL = 9
    HIT_RESPAWN_WAIT = 10
    CELEBRATING = 11
    FINAL_HIT_ANIM = 12
    FINAL_HIT_HOLD = 13
    GAME_OVER = 14


HIT_SEQUENCE_STATES = (
    FelixState.HIT_ANIM,
    FelixState.HIT_FALL,
    FelixState.HIT_RESPAWN_WAIT,
    FelixState.FINAL_HIT_ANIM,
    FelixState.FINAL_HIT_HOLD,
    FelixState.GAME_OVER,
)


HIDDEN_STATES = (FelixState.HIT_RESPAWN_WAIT, FelixState.GAME_OVER)
