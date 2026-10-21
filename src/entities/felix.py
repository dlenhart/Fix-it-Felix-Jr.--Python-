import math
import enum
import pygame
from input_handler import Action
from sprite_data import FELIX_HEAD_CENTER_X
from entities.building import FIX_LAST_WINDOW_SCORE
from level_config import FLOORS_PER_SECTION
from constants import (
    INITIAL_LIVES, BONUS_LIFE_THRESHOLD, INVULNERABLE_TICKS,
    FELIX_MAX_HORIZONTAL_SPEED, FELIX_HORIZONTAL_ACCEL,
    FELIX_HAMMER_START_OFFSET, FELIX_STUN_START_BELOW,
    FELIX_VERTICAL_MOVE_RATE, HAMMER_ANIM_RATE,
    HAMMER_EXTENDED_TICKS, STUN_HOLD_TICKS, DYING_TICKS, SPRITE_FRAME_HOLD_TICKS,
)

COLUMN_COUNT = 5
RESPAWN_LOCAL_ROW = 0
RESPAWN_COLUMN = 2
HITBOX_WIDTH = 12   # [ASSUMED]
HITBOX_HEIGHT = 28  # [ASSUMED]
STUN_RISE_SPEED = 8.0
INVULNERABLE_BLINK_TICKS = 4


class FelixState(enum.Enum):
    IDLE = 0
    WALK_HORIZONTAL = 1
    JUMPING = 4
    HAMMERING = 5
    HAMMER_EXTENDED = 6
    STUNNED = 8
    DYING = 9
    DEATH_HANDLER = 10
    CELEBRATING = 11


class Felix:
    """Felix on the active section: world-space position (center x, feet y)."""

    def __init__(self):
        self.column = RESPAWN_COLUMN
        self.local_row = RESPAWN_LOCAL_ROW
        self.state = FelixState.IDLE
        self.facing_right = True
        self.score = 0
        self.lives = INITIAL_LIVES
        self.last_fixed_points = 0

        self._pos_x = 0.0
        self._pos_y = 0.0
        self._prev_pos_x = 0.0
        self._prev_pos_y = 0.0
        self._vel_x = 0.0
        self._walk_direction = 0
        self._walk_origin_column = 0
        self._target_column = 0
        self._target_row = 0

        self._state_ticks = 0
        self._invulnerable_ticks_remaining = 0
        self._hammer_offset = 0.0
        self._anim_ticks = 0
        self._next_bonus_at = BONUS_LIFE_THRESHOLD
        self._is_placed = False

    @property
    def is_alive(self):
        return self.lives > 0

    @property
    def is_invulnerable(self):
        return self._invulnerable_ticks_remaining > 0

    def place_at(self, local_row, column, building):
        """Put Felix idle on the given cell of the active section."""
        self.local_row = local_row
        self.column = column
        self.state = FelixState.IDLE
        self._vel_x = 0.0
        self._state_ticks = 0
        self._snap_to_anchor(building)
        self._prev_pos_x = self._pos_x
        self._prev_pos_y = self._pos_y
        self._is_placed = True

    def add_score(self, points):
        self.score += points
        while self.score >= self._next_bonus_at:
            self.lives += 1
            self._next_bonus_at += BONUS_LIFE_THRESHOLD

    def hit(self, sound=None):
        """Knock Felix down and cost a life. Returns False if it did not land."""
        if self.is_invulnerable:
            return False
        if self.state in (FelixState.STUNNED, FelixState.DYING, FelixState.DEATH_HANDLER):
            return False
        self.state = FelixState.STUNNED
        self._state_ticks = 0
        self._vel_x = 0.0
        self.lives -= 1
        return True

    def activate_invulnerability(self, sound=None):
        self._invulnerable_ticks_remaining = INVULNERABLE_TICKS
        if sound:
            sound.play_sfx("super_felix")

    def world_pos(self, alpha=1.0):
        """Interpolated (center x, feet y) in world coordinates."""
        x = self._prev_pos_x + (self._pos_x - self._prev_pos_x) * alpha
        y = self._prev_pos_y + (self._pos_y - self._prev_pos_y) * alpha
        return x, y

    def hitbox(self):
        """World-space collision rect, centered on the feet x and standing on the feet y."""
        return pygame.Rect(
            round(self._pos_x - HITBOX_WIDTH / 2),
            round(self._pos_y - HITBOX_HEIGHT),
            HITBOX_WIDTH,
            HITBOX_HEIGHT,
        )

    def tick(self, input_handler, building, sound=None):
        if not self._is_placed:
            self.place_at(self.local_row, self.column, building)
        self.last_fixed_points = 0
        # Snapshot position at the start of this tick so draw() can
        # interpolate toward wherever this tick's movement ends up, keeping
        # motion smooth when render frames and logic ticks drift out of step.
        self._prev_pos_x = self._pos_x
        self._prev_pos_y = self._pos_y
        self._anim_ticks += 1

        if self._invulnerable_ticks_remaining > 0:
            self._invulnerable_ticks_remaining -= 1

        if self.state == FelixState.IDLE:
            self._tick_idle(input_handler, building, sound)
        elif self.state == FelixState.WALK_HORIZONTAL:
            self._tick_walk_horizontal(input_handler, building)
        elif self.state == FelixState.JUMPING:
            self._tick_jumping(building)
        elif self.state == FelixState.HAMMERING:
            self._tick_hammering(sound)
        elif self.state == FelixState.HAMMER_EXTENDED:
            self._tick_hammer_extended(building, sound)
        elif self.state == FelixState.STUNNED:
            self._tick_stunned(building)
        elif self.state == FelixState.DYING:
            self._tick_dying()
        elif self.state == FelixState.DEATH_HANDLER:
            self._tick_death_handler(building, sound)

    def _tick_idle(self, input_handler, building, sound):
        self._snap_to_anchor(building)

        if input_handler.is_just_pressed(Action.JUMP):
            self.state = FelixState.HAMMERING
            self._state_ticks = 0
            self._hammer_offset = FELIX_HAMMER_START_OFFSET
            if sound:
                sound.play_sfx("hammer_hit")
            return

        if input_handler.is_just_pressed(Action.LEFT):
            self._start_walk(-1, sound)
        elif input_handler.is_just_pressed(Action.RIGHT):
            self._start_walk(1, sound)
        elif input_handler.is_just_pressed(Action.UP):
            self._start_jump(1, building, sound)
        elif input_handler.is_just_pressed(Action.DOWN):
            self._start_jump(-1, building, sound)

    def _start_walk(self, direction, sound):
        self.facing_right = direction > 0
        target_column = self.column + direction
        if not 0 <= target_column < COLUMN_COUNT:
            return
        self._walk_direction = direction
        self._walk_origin_column = self.column
        self._target_column = target_column
        self._vel_x = 0.0
        self.state = FelixState.WALK_HORIZONTAL
        self._state_ticks = 0
        if sound:
            sound.play_sfx("felix_move")

    def _start_jump(self, row_step, building, sound):
        target_row = self.local_row + row_step
        if not 0 <= target_row < FLOORS_PER_SECTION:
            return
        if row_step > 0 and self._current_cell(building).has_sill_obstacle:
            return
        self._target_row = target_row
        self.state = FelixState.JUMPING
        self._state_ticks = 0
        if sound:
            sound.play_sfx("jump")

    def _tick_walk_horizontal(self, input_handler, building):
        self._retarget_on_reverse(input_handler)
        target_x = building.cell(self.local_row, self._target_column).center_x
        self._vel_x += self._walk_direction * FELIX_HORIZONTAL_ACCEL
        self._vel_x = max(-FELIX_MAX_HORIZONTAL_SPEED,
                          min(FELIX_MAX_HORIZONTAL_SPEED, self._vel_x))
        self._pos_x += self._vel_x
        has_arrived = (self._walk_direction > 0 and self._pos_x >= target_x) or \
                      (self._walk_direction < 0 and self._pos_x <= target_x)
        if not has_arrived:
            return
        self.column = self._target_column
        self._snap_to_anchor(building)
        self.state = FelixState.IDLE
        self._vel_x = 0.0

    def _retarget_on_reverse(self, input_handler):
        reverse_action = Action.LEFT if self._walk_direction > 0 else Action.RIGHT
        if not input_handler.is_just_pressed(reverse_action):
            return
        self._walk_direction = -self._walk_direction
        self._vel_x = -self._vel_x
        self.facing_right = self._walk_direction > 0
        self._walk_origin_column, self._target_column = (
            self._target_column, self._walk_origin_column)

    def _tick_jumping(self, building):
        target_x, target_y = self._anchor(building, self._target_row, self.column)
        dist_x = target_x - self._pos_x
        dist_y = target_y - self._pos_y
        dist = math.hypot(dist_x, dist_y)

        if dist < FELIX_VERTICAL_MOVE_RATE:
            self.local_row = self._target_row
            self._snap_to_anchor(building)
            self.state = FelixState.IDLE
            return

        self._pos_x += (dist_x / dist) * FELIX_VERTICAL_MOVE_RATE
        self._pos_y += (dist_y / dist) * FELIX_VERTICAL_MOVE_RATE

    def _tick_hammering(self, sound):
        self._state_ticks += 1
        self._hammer_offset += HAMMER_ANIM_RATE
        if self._hammer_offset < 0.0:
            return
        self.state = FelixState.HAMMER_EXTENDED
        self._state_ticks = 0
        if sound:
            sound.play_sfx("hammer_extended")

    def _tick_hammer_extended(self, building, sound):
        self._state_ticks += 1
        if self._state_ticks < HAMMER_EXTENDED_TICKS:
            return
        points = building.fix(self._current_cell(building))
        self.state = FelixState.IDLE
        if not points:
            return
        self.last_fixed_points = points
        self.add_score(points)
        if sound:
            sound.play_sfx("window_fixed" if points == FIX_LAST_WINDOW_SCORE else "hammer_hit")

    def _tick_stunned(self, building):
        self._state_ticks += 1
        anchor_x, anchor_y = self._anchor(building, self.local_row, self.column)
        if self._state_ticks == 1:
            self._pos_x = anchor_x
            self._pos_y = anchor_y + FELIX_STUN_START_BELOW
        if self._state_ticks < STUN_HOLD_TICKS:
            return
        self._pos_y -= STUN_RISE_SPEED
        if self._pos_y > anchor_y:
            return
        self._snap_to_anchor(building)
        if self.lives <= 0:
            self.state = FelixState.DYING
            self._state_ticks = 0
        else:
            self.state = FelixState.IDLE

    def _tick_dying(self):
        self._state_ticks += 1
        if self._state_ticks >= DYING_TICKS:
            self.state = FelixState.DEATH_HANDLER
            self._state_ticks = 0

    def _tick_death_handler(self, building, sound):
        if self.lives <= 0:
            if sound:
                sound.play_sfx("death")
            return
        if sound:
            sound.play_sfx("felix_move")
        self.place_at(RESPAWN_LOCAL_ROW, RESPAWN_COLUMN, building)

    @staticmethod
    def _anchor(building, local_row, column):
        """Standing point: the cell's center x on its floor's bottom y."""
        cell = building.cell(local_row, column)
        floor = building.section_floors()[local_row]
        return cell.center_x, float(floor.bottom_y)

    def _current_cell(self, building):
        return building.cell(self.local_row, self.column)

    def _snap_to_anchor(self, building):
        self._pos_x, self._pos_y = self._anchor(building, self.local_row, self.column)

    def _sprite_name_and_frame(self, sprites):
        if self.state == FelixState.STUNNED:
            return "felix_stunned", 0
        if self.state == FelixState.HAMMERING:
            return ("felix_hammer_right" if self.facing_right else "felix_hammer_left"), 0
        if self.state == FelixState.HAMMER_EXTENDED:
            return ("felix_strike_right" if self.facing_right else "felix_strike_left"), 0
        if self.state in (FelixState.WALK_HORIZONTAL, FelixState.JUMPING):
            name = "felix_walk_right" if self.facing_right else "felix_walk_left"
            frame = (self._anim_ticks // SPRITE_FRAME_HOLD_TICKS) % max(sprites.get_frame_count(name), 1)
            return name, frame
        if self.state == FelixState.CELEBRATING:
            return "felix_celebrate", 0
        return ("felix_idle_right" if self.facing_right else "felix_idle_left"), 0

    def draw(self, screen, sprites, camera, palette, alpha=1.0):
        """Draw bottom-aligned on the feet; hammer frames anchor on the head."""
        is_blink_hidden = self.is_invulnerable and \
            (self._invulnerable_ticks_remaining // INVULNERABLE_BLINK_TICKS) % 2 == 1
        if is_blink_hidden:
            return
        center_x, feet_y = self.world_pos(alpha)
        sprite_name, frame = self._sprite_name_and_frame(sprites)
        sprite = sprites.get_sprite(sprite_name, frame, palette)
        if sprite_name in FELIX_HEAD_CENTER_X:
            left = center_x - FELIX_HEAD_CENTER_X[sprite_name]
        else:
            left = center_x - sprite.get_width() / 2
        top = camera.to_screen_y(feet_y, alpha) - sprite.get_height()
        screen.blit(sprite, (round(left), top))
