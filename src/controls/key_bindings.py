"""Keyboard and gamepad bindings to Actions."""

import pygame

from controls.action import Action

KEYBOARD_MAP = {
    pygame.K_UP: Action.UP,
    pygame.K_DOWN: Action.DOWN,
    pygame.K_LEFT: Action.LEFT,
    pygame.K_RIGHT: Action.RIGHT,
    pygame.K_SPACE: Action.JUMP,
    pygame.K_z: Action.JUMP,
    pygame.K_RETURN: Action.START,
    pygame.K_p: Action.PAUSE,
    pygame.K_ESCAPE: Action.QUIT,
    pygame.K_n: Action.END_GAME,
}

GAMEPAD_BUTTON_MAP = {
    0: Action.JUMP,
    7: Action.START,
    6: Action.QUIT,
}

HAT_MAP = {
    (0, 1): Action.UP,
    (0, -1): Action.DOWN,
    (-1, 0): Action.LEFT,
    (1, 0): Action.RIGHT,
}

AXIS_THRESHOLD = 0.5
