"""A scripted sprite node that animates and draws the way the exe's node list does.

The roof ending drives Felix, Ralph, the Nicelanders, the hatch, the clouds and
the medal as bare exe nodes: a position, a depth and an animation from
roof_data.ROOF_ANIMATIONS.
"""

import pygame

from camera import Camera
from roof_data import Animation, AnimationFrame, AnimationMode
from sprite_sheet import SpriteSheet


class SpriteNode:
    """One exe sprite node (x +0xc, y +0xe, z +0x10, frame +0x12, hold +0x14, flags +0x1a)."""

    def __init__(self, animation: Animation, is_visible: bool = False, is_paused: bool = False):
        self.x = 0
        self.y = 0
        self.z = 0
        self.placement_order = 0
        self.is_visible = is_visible
        self.is_paused = is_paused
        self.is_finished = False
        # +0x1c: the last tick moved the animation onto a new frame.
        self.has_frame_changed = False
        self.animation = animation
        self.frame_index = 0
        self._hold_ticks = animation.frames[0].hold

    @property
    def frame(self) -> AnimationFrame:
        return self.animation.frames[self.frame_index]

    def set_animation(self, animation: Animation) -> None:
        """FUN_0040ecc0: restart on frame 0 and clear the finished and paused flags."""
        self.animation = animation
        self.frame_index = 0
        self._hold_ticks = animation.frames[0].hold
        self.is_finished = False
        self.is_paused = False

    def place(self, x: int, y: int, z: int, placement_order: int) -> None:
        """FUN_0040ecf0: move the node; a re-placed node draws after others of its depth."""
        self.x = x
        self.y = y
        self.z = z
        self.placement_order = placement_order

    def tick(self) -> None:
        """FUN_0040ed40: advance a visible, unpaused, unfinished, non-static animation.

        A frame shows hold + 1 ticks; the frame set by set_animation shows hold
        ticks counted from the tick it was set (its first advance check is the
        same tick, after the script).
        """
        # Cleared for every node first, animating or not.
        self.has_frame_changed = False
        is_animating = (self.is_visible and not self.is_paused and not self.is_finished
                        and self.animation.mode != AnimationMode.STATIC)
        if not is_animating:
            return
        if self._hold_ticks != 0:
            self._hold_ticks -= 1
            return
        self.frame_index += 1
        self.has_frame_changed = True
        frame_count = len(self.animation.frames)
        if self.frame_index >= frame_count:
            if self.animation.mode == AnimationMode.ONCE:
                self.frame_index = frame_count - 1
                self.is_finished = True
            else:
                self.frame_index -= frame_count
        self._hold_ticks = self.frame.hold

    def draw(self, screen: pygame.Surface, sprites: SpriteSheet, camera: Camera,
             palette: int) -> None:
        """FUN_0040ee00: the frame's top-left sits at (x - origin_x, y - origin_y)."""
        if not self.is_visible:
            return
        frame = self.frame
        surface = sprites.get_frame(frame.frame_id, palette)
        screen.blit(surface, (camera.to_screen_x(self.x - frame.origin_x),
                              camera.to_screen_y(self.y - frame.origin_y)))
