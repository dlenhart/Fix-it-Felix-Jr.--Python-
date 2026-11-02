import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from camera import Camera  # noqa: E402


def test_camera_scrolls_without_overshoot():
    camera = Camera()
    arrived = [camera.scroll_toward(5, 2) for _ in range(3)]
    assert arrived == [False, False, True] and camera.scroll_y == 5


def test_to_screen_y_interpolates_between_ticks():
    camera = Camera()
    camera.snapshot()
    camera.scroll_toward(10, 10)
    assert camera.to_screen_y(100, alpha=0.5) == 105
    assert camera.to_screen_y(100) == 110


def test_to_screen_x_adds_the_horizontal_scroll_and_interpolates():
    camera = Camera()
    camera.snapshot()
    camera.scroll_x = -6
    assert camera.to_screen_x(100) == 94
    assert camera.to_screen_x(100, alpha=0.5) == 97


def test_cut_to_jumps_without_interpolation():
    camera = Camera()
    camera.snapshot()
    camera.cut_to(-160, 40)
    assert camera.to_screen_x(304, alpha=0.0) == 144
    assert camera.to_screen_y(0, alpha=0.0) == 40
