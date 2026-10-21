"""Vertical scroll camera for the stacked-floor world (exe scroll offset DAT_0041a248).

No pygame dependency.
"""


class Camera:
    """Holds the vertical scroll offset; screen y = world y + scroll."""

    def __init__(self) -> None:
        self.scroll_y: float = 0.0
        self._previous_scroll_y: float = 0.0

    def snapshot(self) -> None:
        """Remember the current scroll for render interpolation; call once per tick."""
        self._previous_scroll_y = self.scroll_y

    def to_screen_y(self, world_y: float, alpha: float = 1.0) -> int:
        """Convert a world y to a screen y using the scroll interpolated by alpha."""
        interpolated_scroll_y = (
            self._previous_scroll_y + (self.scroll_y - self._previous_scroll_y) * alpha
        )
        return round(world_y + interpolated_scroll_y)

    def scroll_toward(self, target_scroll_y: float, speed: float) -> bool:
        """Move up to `speed` toward the target without overshooting.

        Returns True once the camera is at the target.
        """
        remaining = target_scroll_y - self.scroll_y
        if abs(remaining) <= speed:
            self.scroll_y = target_scroll_y
            return True
        self.scroll_y += speed if remaining > 0 else -speed
        return False
