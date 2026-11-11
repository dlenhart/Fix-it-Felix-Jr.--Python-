"""The game's input vocabulary, independent of keyboard or gamepad."""

import enum


class Action(enum.Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    JUMP = "jump"
    START = "start"
    PAUSE = "pause"
    QUIT = "quit"
    # [EXE] key table: VK 0x4E ('N') sets input bit 0x400; FUN_0040af70 latches it
    # into DAT_004242a6, which ends the game after the next roof sequence.
    END_GAME = "end_game"
