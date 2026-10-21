import random
import pygame
from entities.brick import Brick
from entities.building import GRID_COLS, WINDOW_SPACING_X, GRID_LEFT
from entities.brick import BRICK_FALL_SPEEDS
from constants import (
    RALPH_THROW_BASE_INTERVAL_TICKS, RALPH_THROW_INTERVAL_STEP_TICKS,
    RALPH_THROW_MIN_INTERVAL_TICKS, RALPH_THROW_ANIM_TICKS,
    SPRITE_FRAME_HOLD_TICKS,
)

MAX_BRICKS = 4  # Ghidra-confirmed: 4 brick entity pairs


class Ralph:
    def __init__(self):
        self.x = 90           # Ghidra: Ralph Y position = 0x5A (90)
        self.y = 10
        self.throw_ticks = 0
        self.throw_interval_ticks = RALPH_THROW_BASE_INTERVAL_TICKS
        self.aim_chance = 0.2
        self.bricks_per_throw = 1
        self._anim_ticks = 0
        self._is_throwing = False
        self._throw_anim_ticks = 0

    def configure_for_level(self, level):
        self.throw_interval_ticks = max(
            RALPH_THROW_MIN_INTERVAL_TICKS,
            RALPH_THROW_BASE_INTERVAL_TICKS - (level - 1) * RALPH_THROW_INTERVAL_STEP_TICKS)
        self.aim_chance = min(0.2 + (level - 1) * 0.05, 0.6)
        self.bricks_per_throw = min(1 + (level - 1) // 3, 4)

    def tick(self, felix, building, sound=None):
        """Called once per game tick."""
        new_bricks = []

        self._anim_ticks += 1

        if self._is_throwing:
            self._throw_anim_ticks += 1
            if self._throw_anim_ticks >= RALPH_THROW_ANIM_TICKS:
                self._is_throwing = False

        self.throw_ticks += 1
        if self.throw_ticks >= self.throw_interval_ticks:
            self.throw_ticks = 0
            self._is_throwing = True
            self._throw_anim_ticks = 0
            if sound:
                sound.play_sfx("ralph_grunt")

            for _ in range(self.bricks_per_throw):
                if random.random() < self.aim_chance:
                    target_col = felix.col
                else:
                    target_col = random.randint(0, GRID_COLS - 1)

                brick_x = GRID_LEFT + target_col * WINDOW_SPACING_X + 20
                fall_speed = random.choice(BRICK_FALL_SPEEDS)
                # Ralph's feet sit right at the roofline (his sprite height
                # puts them at ~self.y+54, matching GRID_TOP=64) — spawning
                # from his hands/chest (was +40, only ~14px above the window
                # grid) left almost no visible fall before hitting the top
                # row. Spawn from near his raised throwing arm instead, so
                # every brick has real travel distance before it can hit
                # anything.
                # Falls straight down its column: a random sideways drift
                # compounds over a full-height fall (~180 ticks) and carries
                # bricks off the building entirely.
                brick = Brick(brick_x, self.y + 10, fall_speed)
                new_bricks.append(brick)

        return new_bricks

    def draw(self, screen, sprite_sheet, palette):
        sprite_name = "ralph_throw" if self._is_throwing else "ralph_idle"
        frame = (self._anim_ticks // SPRITE_FRAME_HOLD_TICKS) % 2
        try:
            sprite = sprite_sheet.get_sprite(sprite_name, frame, palette)
            screen.blit(sprite, (int(self.x), int(self.y)))
        except (KeyError, IndexError):
            color = (200, 50, 50) if self._is_throwing else (180, 80, 80)
            pygame.draw.rect(screen, color, (int(self.x), int(self.y), 60, 70))
            pygame.draw.circle(screen, (220, 160, 120),
                (int(self.x) + 30, int(self.y) + 15), 15)
