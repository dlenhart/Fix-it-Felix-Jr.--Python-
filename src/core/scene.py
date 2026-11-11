"""Base class for screens driven by the SceneManager."""


class Scene:
    def __init__(self, manager):
        self.manager = manager

    def tick(self, input_handler):
        """Called once per game tick (TICKS_PER_SECOND times a second). All game logic goes here."""
        pass

    def draw(self, screen, alpha=1.0):
        """Called every render frame (60fps). Only drawing, no logic.

        alpha is how far we are between the last completed game tick and
        the next one (0..1) — entities use it to interpolate their
        rendered position for smooth motion despite the slower tick rate.
        """
        pass

    def on_enter(self):
        pass

    def on_exit(self):
        pass
