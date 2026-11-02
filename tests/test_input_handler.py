import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402
import pytest  # noqa: E402

from input_handler import (  # noqa: E402
    GAMEPAD_BUTTON_MAP, HAT_MAP, KEYBOARD_MAP, Action, InputHandler,
)

pygame.init()


class HeldKeys:
    """Stands in for pygame.key.get_pressed(): indexable by key code."""

    def __init__(self, *held_keys):
        self._held_keys = set(held_keys)

    def __getitem__(self, key):
        return key in self._held_keys


class FakeJoystick:
    def __init__(self, buttons=(), hat=(0, 0), axes=(0.0, 0.0)):
        self._buttons = set(buttons)
        self._hat = hat
        self._axes = axes

    def init(self):
        pass

    def get_numbuttons(self):
        return 8

    def get_button(self, index):
        return index in self._buttons

    def get_numhats(self):
        return 1

    def get_hat(self, index):
        return self._hat

    def get_numaxes(self):
        return len(self._axes)

    def get_axis(self, index):
        return self._axes[index]


@pytest.fixture
def keyboard(monkeypatch):
    """Returns a setter for the keys currently held; no joystick is attached."""
    monkeypatch.setattr(pygame.joystick, "get_count", lambda: 0)
    held = {"keys": HeldKeys()}
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: held["keys"])

    def hold(*keys):
        held["keys"] = HeldKeys(*keys)
    return hold


def test_just_pressed_latches_across_polls_until_consumed(keyboard):
    handler = InputHandler()
    keyboard(pygame.K_SPACE)
    handler.poll([])
    keyboard()  # released before any game tick ran
    handler.poll([])
    assert handler.is_just_pressed(Action.JUMP)
    handler.consume_just_pressed()
    assert not handler.is_just_pressed(Action.JUMP)


def test_held_key_is_pressed_but_not_just_pressed_after_consume(keyboard):
    handler = InputHandler()
    keyboard(pygame.K_LEFT)
    handler.poll([])
    handler.consume_just_pressed()
    handler.poll([])
    assert handler.is_pressed(Action.LEFT)
    assert not handler.is_just_pressed(Action.LEFT)


def test_keyup_clears_pressed(keyboard):
    handler = InputHandler()
    keyboard(pygame.K_RIGHT)
    handler.poll([])
    assert handler.is_pressed(Action.RIGHT)
    keyboard()
    handler.poll([])
    assert not handler.is_pressed(Action.RIGHT)


def test_every_keyboard_map_entry_maps_to_an_action(keyboard):
    handler = InputHandler()
    for key, action in KEYBOARD_MAP.items():
        assert isinstance(action, Action)
        keyboard(key)
        handler.poll([])
        assert handler.is_pressed(action), f"key {key} did not press {action}"


def test_focus_loss_reported_until_consumed(keyboard):
    handler = InputHandler()
    assert not handler.has_lost_focus()
    handler.poll([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
    handler.poll([])
    assert handler.has_lost_focus()
    handler.consume_just_pressed()
    assert not handler.has_lost_focus()


@pytest.fixture
def attach_joystick(monkeypatch, keyboard):
    """Returns a function that makes the next InputHandler find the given joystick."""
    def attach(joystick):
        monkeypatch.setattr(pygame.joystick, "get_count", lambda: 1)
        monkeypatch.setattr(pygame.joystick, "Joystick", lambda index: joystick)
    return attach


def poll_with_joystick(attach_joystick, joystick):
    attach_joystick(joystick)
    handler = InputHandler()
    handler.poll([])
    return handler


def test_gamepad_buttons_map_to_actions(attach_joystick):
    handler = poll_with_joystick(
        attach_joystick, FakeJoystick(buttons=GAMEPAD_BUTTON_MAP.keys()))
    for action in GAMEPAD_BUTTON_MAP.values():
        assert handler.is_pressed(action)


def test_gamepad_hat_maps_to_directions(attach_joystick):
    for hat, action in HAT_MAP.items():
        handler = poll_with_joystick(attach_joystick, FakeJoystick(hat=hat))
        assert handler.is_pressed(action)


def test_gamepad_axes_past_threshold_map_to_directions(attach_joystick):
    handler = poll_with_joystick(attach_joystick, FakeJoystick(axes=(-0.9, 0.9)))
    assert handler.is_pressed(Action.LEFT) and handler.is_pressed(Action.DOWN)
    handler = poll_with_joystick(attach_joystick, FakeJoystick(axes=(0.9, -0.9)))
    assert handler.is_pressed(Action.RIGHT) and handler.is_pressed(Action.UP)


def test_gamepad_axes_inside_dead_zone_press_nothing(attach_joystick):
    handler = poll_with_joystick(attach_joystick, FakeJoystick(axes=(0.2, -0.2)))
    assert not any(handler.is_pressed(action) for action in Action)


def test_joystick_removed_event_stops_gamepad_input(attach_joystick):
    attach_joystick(FakeJoystick(buttons=(0,)))
    handler = InputHandler()
    handler.poll([pygame.event.Event(pygame.JOYDEVICEREMOVED)])
    assert not handler.is_pressed(Action.JUMP)


def test_joystick_added_event_attaches_the_gamepad(keyboard, attach_joystick):
    handler = InputHandler()
    attach_joystick(FakeJoystick(buttons=(0,)))
    handler.poll([pygame.event.Event(pygame.JOYDEVICEADDED)])
    assert handler.is_pressed(Action.JUMP)
