import math
import enum
import pygame
from input_handler import Action
from entities.building import GRID_COLS, WINDOW_WIDTH, WINDOW_HEIGHT
from constants import (
    INITIAL_LIVES, BONUS_LIFE_THRESHOLD, SUPER_DURATION_TICKS,
    FELIX_MAX_HORIZONTAL_SPEED,
    FELIX_FALL_TERMINAL_VEL, FELIX_HAMMER_START_OFFSET,
    FELIX_STUN_KNOCKBACK_Y,
    FELIX_VERTICAL_MOVE_RATE, FELIX_GRAVITY_ACCEL, HAMMER_ANIM_RATE,
)


class FelixState(enum.Enum):
    IDLE = 0
    WALK_HORIZONTAL = 1
    WALK_VERTICAL = 3
    JUMPING = 4
    HAMMERING = 5
    HAMMER_EXTENDED = 6
    FALLING = 7
    STUNNED = 8
    DYING = 9
    DEATH_HANDLER = 10
    CELEBRATING = 11


class Felix:
    def __init__(self):
        self.col = 2
        self.row = 0
        self.state = FelixState.IDLE
        self.facing_right = True
        self.score = 0
        self.lives = INITIAL_LIVES
        self.is_super = False

        self._pos_x = 0.0
        self._pos_y = 0.0
        self._prev_pos_x = 0.0
        self._prev_pos_y = 0.0
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._target_x = 0.0
        self._target_y = 0.0
        self._move_target_col = 0
        self._move_target_row = 0

        self._state_ticks = 0
        self._super_ticks = 0
        self._hammer_offset = 0.0
        self._hammer_phase = 0
        self._anim_frame = 0
        self._next_bonus_at = BONUS_LIFE_THRESHOLD
        self._pos_initialized = False

    @property
    def is_alive(self):
        return self.lives > 0

    def _init_pos(self, building):
        if not self._pos_initialized:
            px, py = building.get_window_pixel_pos(self.col, self.row)
            self._pos_x = float(px)
            self._pos_y = float(py)
            self._pos_initialized = True

    def reset_position(self):
        self.col = 2
        self.row = 0
        self.state = FelixState.IDLE
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._state_ticks = 0
        self._pos_initialized = False

    def add_score(self, points):
        self.score += points
        while self.score >= self._next_bonus_at:
            self.lives += 1
            self._next_bonus_at += BONUS_LIFE_THRESHOLD

    def stun(self, sound=None):
        if self.is_super or self.state == FelixState.STUNNED:
            return
        self.state = FelixState.STUNNED
        self._state_ticks = 0
        self._vel_x = 0.0
        self._vel_y = 0.0
        self.lives -= 1

    def activate_super(self, sound=None):
        self.is_super = True
        self._super_ticks = 0
        if sound:
            sound.play_sfx("super_felix")

    def tick(self, input_handler, building, sound=None):
        self._init_pos(building)
        # Snapshot position at the start of this tick so draw() can
        # interpolate toward wherever this tick's movement ends up,
        # smoothing motion across the ~15 render frames between ticks.
        self._prev_pos_x = self._pos_x
        self._prev_pos_y = self._pos_y
        self._anim_frame = (self._anim_frame + 1) % 4

        if self.is_super:
            self._super_ticks += 1
            if self._super_ticks >= SUPER_DURATION_TICKS:
                self.is_super = False

        if self.state == FelixState.IDLE:
            self._tick_idle(input_handler, building, sound)
        elif self.state == FelixState.WALK_HORIZONTAL:
            self._tick_walk_horizontal(building, sound)
        elif self.state == FelixState.WALK_VERTICAL:
            self._tick_walk_vertical(building, sound)
        elif self.state == FelixState.JUMPING:
            self._tick_jumping(building, sound)
        elif self.state == FelixState.HAMMERING:
            self._tick_hammering(building, sound)
        elif self.state == FelixState.HAMMER_EXTENDED:
            self._tick_hammer_extended(building, sound)
        elif self.state == FelixState.FALLING:
            self._tick_falling(building, sound)
        elif self.state == FelixState.STUNNED:
            self._tick_stunned(building, sound)
        elif self.state == FelixState.DYING:
            self._tick_dying(sound)
        elif self.state == FelixState.DEATH_HANDLER:
            self._tick_death_handler(sound)

    def _tick_idle(self, input_handler, building, sound):
        self._snap_to_grid(building)

        if input_handler.is_just_pressed(Action.JUMP):
            self.state = FelixState.HAMMERING
            self._state_ticks = 0
            self._hammer_offset = FELIX_HAMMER_START_OFFSET
            self._hammer_phase = 0
            if sound:
                sound.play_sfx("hammer_hit")
            return

        dx, dy = 0, 0
        if input_handler.is_just_pressed(Action.LEFT):
            dx = -1
            self.facing_right = False
        elif input_handler.is_just_pressed(Action.RIGHT):
            dx = 1
            self.facing_right = True
        elif input_handler.is_just_pressed(Action.UP):
            dy = -1
        elif input_handler.is_just_pressed(Action.DOWN):
            dy = 1

        if dx != 0:
            new_col = self.col + dx
            if 0 <= new_col < GRID_COLS:
                self._move_target_col = new_col
                self._move_target_row = self.row
                tx, ty = building.get_window_pixel_pos(new_col, self.row)
                self._target_x = float(tx)
                self._target_y = float(ty)
                self._vel_x = FELIX_MAX_HORIZONTAL_SPEED * dx
                self._vel_y = 0.0
                self.state = FelixState.WALK_HORIZONTAL
                self._state_ticks = 0
                if sound:
                    sound.play_sfx("felix_move")
        elif dy != 0:
            new_row = self.row + dy
            if 0 <= new_row < building.current_rows:
                self._move_target_col = self.col
                self._move_target_row = new_row
                tx, ty = building.get_window_pixel_pos(self.col, new_row)
                self._target_x = float(tx)
                self._target_y = float(ty)
                self._vel_x = 0.0
                self._vel_y = FELIX_VERTICAL_MOVE_RATE * dy
                self.state = FelixState.JUMPING
                self._state_ticks = 0
                if sound:
                    sound.play_sfx("jump")

    def _tick_walk_horizontal(self, building, sound):
        self._pos_x += self._vel_x
        arrived = (self._vel_x > 0 and self._pos_x >= self._target_x) or \
                  (self._vel_x < 0 and self._pos_x <= self._target_x)
        if arrived:
            self.col = self._move_target_col
            self.row = self._move_target_row
            self._snap_to_grid(building)
            self.state = FelixState.IDLE
            self._vel_x = 0.0

    def _tick_walk_vertical(self, building, sound):
        self._pos_y += self._vel_y
        arrived = (self._vel_y > 0 and self._pos_y >= self._target_y) or \
                  (self._vel_y < 0 and self._pos_y <= self._target_y)
        if arrived:
            self.col = self._move_target_col
            self.row = self._move_target_row
            self._snap_to_grid(building)
            self.state = FelixState.IDLE
            self._vel_y = 0.0

    def _tick_jumping(self, building, sound):
        dist_x = self._target_x - self._pos_x
        dist_y = self._target_y - self._pos_y
        dist = math.sqrt(dist_x * dist_x + dist_y * dist_y)

        if dist < FELIX_VERTICAL_MOVE_RATE:
            self.col = self._move_target_col
            self.row = self._move_target_row
            self._snap_to_grid(building)
            self.state = FelixState.IDLE
            self._vel_x = 0.0
            self._vel_y = 0.0
            return

        speed = FELIX_VERTICAL_MOVE_RATE
        self._pos_x += (dist_x / dist) * speed
        self._pos_y += (dist_y / dist) * speed

    def _tick_hammering(self, building, sound):
        self._state_ticks += 1
        self._hammer_offset += HAMMER_ANIM_RATE
        if self._hammer_offset >= 0.0:
            self._hammer_phase = 1
            self.state = FelixState.HAMMER_EXTENDED
            self._state_ticks = 0
            if sound:
                sound.play_sfx("hammer_extended")

    def _tick_hammer_extended(self, building, sound):
        self._state_ticks += 1
        if self._state_ticks >= 2:
            repaired, fully_fixed = building.repair_window(
                self.col, self.row, is_super=self.is_super
            )
            if repaired:
                self.add_score(100)
                if sound:
                    sound.play_sfx("hammer_hit")
            if fully_fixed:
                self.add_score(500)
                if sound:
                    sound.play_sfx("window_fixed")
            self.state = FelixState.IDLE

    def _tick_falling(self, building, sound):
        self._vel_y += FELIX_GRAVITY_ACCEL
        if self._vel_y > FELIX_FALL_TERMINAL_VEL:
            self._vel_y = FELIX_FALL_TERMINAL_VEL
        self._pos_y += self._vel_y
        px, py = building.get_window_pixel_pos(self.col, self.row)
        if self._pos_y >= py:
            self._snap_to_grid(building)
            self.state = FelixState.IDLE
            self._vel_y = 0.0

    def _tick_stunned(self, building, sound):
        self._state_ticks += 1
        target_x, target_y = building.get_window_pixel_pos(self.col, self.row)
        if self._state_ticks == 1:
            self._pos_y = FELIX_STUN_KNOCKBACK_Y
        if self._state_ticks < 4:
            return
        fall_speed = 8.0
        self._pos_y -= fall_speed
        if self._pos_y <= target_y:
            self._snap_to_grid(building)
            if self.lives <= 0:
                self.state = FelixState.DYING
                self._state_ticks = 0
            else:
                self.state = FelixState.IDLE

    def _tick_dying(self, sound):
        self._state_ticks += 1
        if self._state_ticks >= 4:
            self.state = FelixState.DEATH_HANDLER
            self._state_ticks = 0

    def _tick_death_handler(self, sound):
        if self.lives <= 0:
            if sound:
                sound.play_sfx("death")
            return
        if sound:
            sound.play_sfx("felix_move")
        self.reset_position()

    def _snap_to_grid(self, building):
        px, py = building.get_window_pixel_pos(self.col, self.row)
        self._pos_x = float(px)
        self._pos_y = float(py)

    def get_pixel_pos(self, building, alpha=1.0):
        self._init_pos(building)
        x = self._prev_pos_x + (self._pos_x - self._prev_pos_x) * alpha
        y = self._prev_pos_y + (self._pos_y - self._prev_pos_y) * alpha
        return int(x), int(y)

    def draw(self, screen, sprite_sheet, palette, building, alpha=1.0):
        px, py = self.get_pixel_pos(building, alpha)

        sprite_name = "felix_idle_right"
        frame = 0

        if self.state == FelixState.STUNNED:
            sprite_name = "felix_stunned"
        elif self.state in (FelixState.HAMMERING, FelixState.HAMMER_EXTENDED):
            sprite_name = "felix_hammer_right" if self.facing_right else "felix_hammer_left"
        elif self.state in (FelixState.WALK_HORIZONTAL, FelixState.WALK_VERTICAL,
                            FelixState.JUMPING):
            sprite_name = "felix_walk_right" if self.facing_right else "felix_walk_left"
            frame = self._anim_frame % max(sprite_sheet.get_frame_count(sprite_name), 1)
        elif self.state == FelixState.CELEBRATING:
            sprite_name = "felix_celebrate"
        else:
            sprite_name = "felix_idle_right" if self.facing_right else "felix_idle_left"

        try:
            sprite = sprite_sheet.get_sprite(sprite_name, frame, palette)
            offset_x = (WINDOW_WIDTH - sprite.get_width()) // 2
            offset_y = WINDOW_HEIGHT - sprite.get_height()
            screen.blit(sprite, (px + offset_x, py + offset_y))
        except (KeyError, IndexError):
            color = (255, 255, 0) if self.is_super else (0, 100, 255)
            pygame.draw.rect(screen, color, (px + 4, py + 4, 16, 24))
            pygame.draw.circle(screen, (255, 200, 150), (px + 12, py + 6), 5)

        if self.is_super:
            flash = pygame.Surface((16, 24), pygame.SRCALPHA)
            flash.fill((255, 255, 100, 80))
            screen.blit(flash, (px + 4, py + 4))
