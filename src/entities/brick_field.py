"""Every live brick: spawning, the per-section window-break budget and collisions."""

import random

import pygame

from audio.sound_sink import SILENT_SOUND, SoundSink
from constants.bricks import (
    BRICK_MAX_LIVE, BRICK_WINDOW_BREAK_MIN_LEVEL, BRICK_WINDOW_BREAK_ODDS, BRICK_WINDOW_BREAK_ROLL,
    BRICK_WINDOW_BREAKS_PER_SECTION, GROUND_Y,
)
from core.camera import Camera
from entities.brick import Brick
from entities.felix import Felix
from graphics.sprite_sheet import SpriteSheet
from world.building import Building


class BrickField:
    """Owns every live brick and resolves their collisions each tick."""

    def __init__(self, rng: random.Random):
        self._rng = rng
        self._bricks: list[Brick] = []
        self._window_break_budget = BRICK_WINDOW_BREAKS_PER_SECTION

    @property
    def live_count(self) -> int:
        return len(self._bricks)

    @property
    def bricks(self) -> tuple[Brick, ...]:
        """The live bricks, as a snapshot."""
        return tuple(self._bricks)

    def spawn(self, x: float, y: float) -> None:
        if len(self._bricks) >= BRICK_MAX_LIVE:
            return
        self._bricks.append(Brick(x, y))

    def clear(self) -> None:
        self._bricks.clear()

    def is_falling_toward(self, hitbox: pygame.Rect) -> bool:
        """True if a falling brick is above the hitbox's feet and overlaps it horizontally.

        Bouncing bricks and bricks already past the feet can't hit it. Deliberately
        conservative: a brick several floors up still counts, however long it needs.
        """
        for brick in self._bricks:
            if brick.is_bouncing:
                continue
            brick_rect = brick.rect()
            is_overlapping_horizontally = (brick_rect.left < hitbox.right
                                           and hitbox.left < brick_rect.right)
            if is_overlapping_horizontally and brick_rect.bottom <= hitbox.bottom:
                return True
        return False

    def reset_break_budget(self) -> None:
        self._window_break_budget = BRICK_WINDOW_BREAKS_PER_SECTION

    def tick(self, building: Building, felix: Felix, level: int,
             sound: SoundSink = SILENT_SOUND) -> bool:
        """Advance every brick. Returns True if Felix was hit this tick."""
        was_felix_hit = False
        for brick in self._bricks:
            if brick.is_bouncing:
                brick.tick_bounce()
                continue
            brick.tick_fall()
            if brick.rect().colliderect(felix.hitbox()):
                if felix.is_invulnerable:
                    brick.start_bounce(self._rng)
                    sound.play_sfx("brick_bounce")  # FUN_0040d490: sound 3
                    continue
                # The brick vanishes even if Felix is already in the hit sequence (ruling R3).
                if felix.hit(sound):
                    was_felix_hit = True
                    sound.play_sfx("felix_hit")  # FUN_0040d490: sound 0, then FUN_0040ca00
                brick.is_active = False
                continue
            if self._try_break_window(brick, building, level, sound):
                brick.is_active = False
                continue
            if brick.y >= GROUND_Y:
                brick.start_bounce(self._rng)
        self._bricks = [brick for brick in self._bricks if brick.is_active]
        return was_felix_hit

    def draw(self, screen, sprites: SpriteSheet, camera: Camera, palette, alpha: float) -> None:
        for brick in self._bricks:
            brick.draw(screen, sprites, camera, palette, alpha)

    def _try_break_window(self, brick: Brick, building: Building, level: int, sound) -> bool:
        if level < BRICK_WINDOW_BREAK_MIN_LEVEL or self._window_break_budget <= 0:
            return False
        brick_rect = brick.rect()
        for floor in building.section_floors():
            for cell in floor.cells:
                if not cell.is_damageable or cell.is_broken:
                    continue
                if not brick_rect.colliderect(building.glass_rect(cell)):
                    continue
                if self._rng.randrange(BRICK_WINDOW_BREAK_ODDS) != BRICK_WINDOW_BREAK_ROLL:
                    continue
                building.damage(cell, is_heavy=False, sound=sound)
                self._window_break_budget -= 1
                return True
        return False
