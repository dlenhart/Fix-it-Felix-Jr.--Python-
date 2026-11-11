import pygame

from controls.action import Action
from controls.key_bindings import AXIS_THRESHOLD, GAMEPAD_BUTTON_MAP, HAT_MAP, KEYBOARD_MAP


class InputHandler:
    def __init__(self):
        self._pressed = set()
        self._just_pressed = set()
        self._has_lost_focus = False
        self._joystick = None
        self._init_joystick()

    def _init_joystick(self):
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

    def poll(self, events):
        # poll() runs once per render frame, but game logic only consumes
        # is_just_pressed() once per fixed-step tick. The two rates don't stay
        # in lockstep (a slow frame runs 0 or 2+ ticks), and a key transition
        # lasts exactly one poll(), so without latching it here a press can
        # be cleared before any tick sees it.
        # just_pressed accumulates across polls until consume_just_pressed()
        # is called once per tick.
        prev_pressed = self._pressed.copy()
        self._pressed.clear()

        for event in events:
            if event.type == pygame.JOYDEVICEADDED:
                self._init_joystick()
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._joystick = None
            elif event.type == pygame.WINDOWFOCUSLOST:
                self._has_lost_focus = True

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

        self._just_pressed |= (self._pressed - prev_pressed)

    def consume_just_pressed(self):
        """Call once per game-logic tick, after it has read is_just_pressed()."""
        self._just_pressed.clear()
        self._has_lost_focus = False

    def has_lost_focus(self):
        """True if the window lost focus since the last tick. Latched like
        is_just_pressed() so a tick can't miss it between polls."""
        return self._has_lost_focus

    def is_pressed(self, action):
        return action in self._pressed

    def is_just_pressed(self, action):
        return action in self._just_pressed
