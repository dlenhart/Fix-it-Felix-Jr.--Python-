"""Scroll camera for the stacked-floor world.

Vertical offset is the exe's DAT_0041a248, horizontal offset DAT_0041a298:
FUN_0040ee00 and FUN_0040f140 both draw at screen = world + offset. Play only
scrolls vertically; the roof ending also pans and cuts horizontally.

No pygame dependency.
"""


class Camera:
    """Holds the scroll offsets; screen x = world x + scroll_x, screen y = world y + scroll_y."""

    def __init__(self) -> None:
        self.scroll_x: float = 0.0
        self.scroll_y: float = 0.0
        self._previous_scroll_x: float = 0.0
        self._previous_scroll_y: float = 0.0

    def snapshot(self) -> None:
        """Remember the current scroll for render interpolation; call once per tick."""
        self._previous_scroll_x = self.scroll_x
        self._previous_scroll_y = self.scroll_y

    def cut_to(self, scroll_x: float, scroll_y: float) -> None:
        """Jump to a scroll with no interpolation from the previous one (a camera cut)."""
        self.scroll_x = scroll_x
        self.scroll_y = scroll_y
        self._previous_scroll_x = scroll_x
        self._previous_scroll_y = scroll_y

    def to_screen_x(self, world_x: float, alpha: float = 1.0) -> int:
        """Convert a world x to a screen x using the scroll interpolated by alpha."""
        interpolated_scroll_x = (
            self._previous_scroll_x + (self.scroll_x - self._previous_scroll_x) * alpha
        )
        return round(world_x + interpolated_scroll_x)

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
