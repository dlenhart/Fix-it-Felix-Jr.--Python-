import enum
import pygame


class Action(enum.Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    JUMP = "jump"
    START = "start"
    QUIT = "quit"


KEYBOARD_MAP = {
    pygame.K_UP: Action.UP,
    pygame.K_DOWN: Action.DOWN,
    pygame.K_LEFT: Action.LEFT,
    pygame.K_RIGHT: Action.RIGHT,
    pygame.K_SPACE: Action.JUMP,
    pygame.K_z: Action.JUMP,
    pygame.K_RETURN: Action.START,
    pygame.K_ESCAPE: Action.QUIT,
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


class InputHandler:
    def __init__(self):
        self._pressed = set()
        self._just_pressed = set()
        self._joystick = None
        self._init_joystick()

    def _init_joystick(self):
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

    def poll(self, events):
        self._just_pressed.clear()
        prev_pressed = self._pressed.copy()
        self._pressed.clear()

        for event in events:
            if event.type == pygame.JOYDEVICEADDED:
                self._init_joystick()
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._joystick = None

        keys = pygame.key.get_pressed()
        for key, action in KEYBOARD_MAP.items():
            if keys[key]:
                self._pressed.add(action)

        if self._joystick:
            for btn, action in GAMEPAD_BUTTON_MAP.items():
                if btn < self._joystick.get_numbuttons() and self._joystick.get_button(btn):
                    self._pressed.add(action)

            if self._joystick.get_numhats() > 0:
                hat = self._joystick.get_hat(0)
                if hat in HAT_MAP:
                    self._pressed.add(HAT_MAP[hat])

            if self._joystick.get_numaxes() >= 2:
                x_axis = self._joystick.get_axis(0)
                y_axis = self._joystick.get_axis(1)
                if x_axis < -AXIS_THRESHOLD:
                    self._pressed.add(Action.LEFT)
                elif x_axis > AXIS_THRESHOLD:
                    self._pressed.add(Action.RIGHT)
                if y_axis < -AXIS_THRESHOLD:
                    self._pressed.add(Action.UP)
                elif y_axis > AXIS_THRESHOLD:
                    self._pressed.add(Action.DOWN)

        self._just_pressed = self._pressed - prev_pressed

    def is_pressed(self, action):
        return action in self._pressed

    def is_just_pressed(self, action):
        return action in self._just_pressed
