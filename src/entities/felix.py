import math
import enum
import pygame
from input_handler import Action
from sprite_data import (
    FELIX_HEAD_CENTER_X,
    FELIX_HIT_FRAMES_RIGHT, FELIX_HIT_FRAMES_LEFT, FELIX_HIT_FRAME_HOLD_TICKS,
    FELIX_FINAL_HIT_FRAMES, FELIX_FINAL_HIT_FRAME_HOLD_TICKS,
)
from entities.building import FIX_LAST_WINDOW_SCORE
from level_config import FLOORS_PER_SECTION, STREET_Y
from constants import (
    INITIAL_LIVES, BONUS_LIFE_THRESHOLD, INVULNERABLE_TICKS,
    FELIX_MAX_HORIZONTAL_SPEED, FELIX_HORIZONTAL_ACCEL,
    FELIX_HAMMER_START_OFFSET,
    FELIX_VERTICAL_MOVE_RATE, HAMMER_ANIM_RATE,
    HAMMER_EXTENDED_TICKS, SPRITE_FRAME_HOLD_TICKS,
)

COLUMN_COUNT = 5
RESPAWN_LOCAL_ROW = 0
RESPAWN_COLUMN = 2
HITBOX_WIDTH = 12   # [ASSUMED]
HITBOX_HEIGHT = 28  # [ASSUMED]
INVULNERABLE_BLINK_TICKS = 4

FELIX_HIT_FALL_GRAVITY = 0.33  # [EXE] double at 0x416be8, FUN_0040c1a0
FELIX_HIT_FALL_BELOW_STREET = 0x28  # [EXE] FUN_0040c1a0: building bottom + 0x28
FELIX_RESPAWN_DELAY_TICKS = 60  # [EXE] FUN_0040c1a0 (0x3c)
FELIX_FINAL_HIT_SETTLE_FRAME_INDEX = 7  # [EXE] FUN_0040c1a0 waits for anim frame 7
FELIX_GAME_OVER_DELAY_TICKS = 120  # [EXE] FUN_0040c1a0 (0x78) before the game-over state


def _frame_display_ticks(hold_ticks):
    # FUN_0040ed40 counts a frame's hold down to zero before advancing,
    # so each frame stays up for hold + 1 ticks.
    return hold_ticks + 1


HIT_ANIM_TICKS = len(FELIX_HIT_FRAMES_RIGHT) * _frame_display_ticks(FELIX_HIT_FRAME_HOLD_TICKS)


class FelixState(enum.Enum):
    IDLE = 0
    WALK_HORIZONTAL = 1
    JUMPING = 4
    HAMMERING = 5
    HAMMER_EXTENDED = 6
    HIT_ANIM = 8
    HIT_FALL = 9
    HIT_RESPAWN_WAIT = 10
    CELEBRATING = 11
    FINAL_HIT_ANIM = 12
    FINAL_HIT_HOLD = 13
    GAME_OVER = 14


HIT_SEQUENCE_STATES = (
    FelixState.HIT_ANIM,
    FelixState.HIT_FALL,
    FelixState.HIT_RESPAWN_WAIT,
    FelixState.FINAL_HIT_ANIM,
    FelixState.FINAL_HIT_HOLD,
    FelixState.GAME_OVER,
)
HIDDEN_STATES = (FelixState.HIT_RESPAWN_WAIT, FelixState.GAME_OVER)


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
        self._vel_y = 0.0
        self._walk_direction = 0
        self._walk_origin_column = 0
        self._target_column = 0
        self._target_row = 0

        self._state_ticks = 0
        self._invulnerable_ticks_remaining = 0
        self._hammer_offset = 0.0
        self._anim_ticks = 0
        self._hit_anim_ticks = 0
        self._next_bonus_at = BONUS_LIFE_THRESHOLD
        self._is_placed = False

    @property
    def is_alive(self):
        return self.lives > 0

    @property
    def is_game_over(self):
        """True once the last life's hit sequence has played out."""
        return self.state == FelixState.GAME_OVER

    @property
    def is_in_hit_sequence(self):
        """True from a landed hit until the respawn; for good after the last life's hit."""
        return self.state in HIT_SEQUENCE_STATES

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
        """Start the hit sequence (FUN_0040ca00). Returns False if it did not land.

        The life is lost at the respawn, as in the exe; on the last life Felix
        never respawns and lives drop to 0 when the sequence ends.
        """
        if self.is_invulnerable:
            return False
        if self.is_in_hit_sequence:
            return False
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._state_ticks = 0
        self._hit_anim_ticks = 0
        if self.lives > 1:
            self.state = FelixState.HIT_ANIM
            return True
        self.state = FelixState.FINAL_HIT_ANIM
        if sound:
            sound.play_sfx("death")
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
        elif self.state == FelixState.HIT_ANIM:
            self._tick_hit_anim()
        elif self.state == FelixState.HIT_FALL:
            self._tick_hit_fall()
        elif self.state == FelixState.HIT_RESPAWN_WAIT:
            self._tick_hit_respawn_wait(building)
        elif self.state == FelixState.FINAL_HIT_ANIM:
            self._tick_final_hit_anim()
        elif self.state == FelixState.FINAL_HIT_HOLD:
            self._tick_final_hit_hold()

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

    def _tick_hit_anim(self):
        self._hit_anim_ticks += 1
        if self._hit_anim_ticks < HIT_ANIM_TICKS:
            return
        self.state = FelixState.HIT_FALL
        self._vel_y = 0.0

    def _tick_hit_fall(self):
        self._vel_y += FELIX_HIT_FALL_GRAVITY
        self._pos_y += self._vel_y
        if self._pos_y <= STREET_Y + FELIX_HIT_FALL_BELOW_STREET:
            return
        self.state = FelixState.HIT_RESPAWN_WAIT
        self._state_ticks = FELIX_RESPAWN_DELAY_TICKS

    def _tick_hit_respawn_wait(self, building):
        self._state_ticks -= 1
        if self._state_ticks > 0:
            return
        self.lives -= 1
        # The same cell he was on, not the one a walk or jump was heading for.
        self.place_at(self.local_row, self.column, building)

    def _tick_final_hit_anim(self):
        self._hit_anim_ticks += 1
        frame_index = _frame_index_after(FELIX_FINAL_HIT_FRAME_HOLD_TICKS, self._hit_anim_ticks)
        if frame_index < FELIX_FINAL_HIT_SETTLE_FRAME_INDEX:
            return
        self.state = FelixState.FINAL_HIT_HOLD
        self._state_ticks = FELIX_GAME_OVER_DELAY_TICKS

    def _tick_final_hit_hold(self):
        # The final animation keeps playing (it lands on the halo frame) while the hold runs.
        self._hit_anim_ticks += 1
        self._state_ticks -= 1
        if self._state_ticks > 0:
            return
        self.lives = 0
        self.state = FelixState.GAME_OVER

    @staticmethod
    def _anchor(building, local_row, column):
        """Standing point: the cell's center x on its sill (the exe's cell+0x74)."""
        cell = building.cell(local_row, column)
        return cell.center_x, float(building.sill_y(cell))

    def _current_cell(self, building):
        return building.cell(self.local_row, self.column)

    def _snap_to_anchor(self, building):
        self._pos_x, self._pos_y = self._anchor(building, self.local_row, self.column)

    def _hit_frame_id(self):
        if self.state in (FelixState.FINAL_HIT_ANIM, FelixState.FINAL_HIT_HOLD):
            index = _frame_index_after(FELIX_FINAL_HIT_FRAME_HOLD_TICKS, self._hit_anim_ticks)
            return FELIX_FINAL_HIT_FRAMES[index]
        frames = FELIX_HIT_FRAMES_RIGHT if self.facing_right else FELIX_HIT_FRAMES_LEFT
        holds = (FELIX_HIT_FRAME_HOLD_TICKS,) * len(frames)
        # The fall keeps showing the animation's last frame.
        return frames[_frame_index_after(holds, self._hit_anim_ticks)]

    def _sprite_name_and_frame(self, sprites):
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
        if self.state in HIDDEN_STATES:
            return
        center_x, feet_y = self.world_pos(alpha)
        if self.is_in_hit_sequence:
            self._draw_hit_frame(screen, sprites, camera, palette, center_x, feet_y, alpha)
            return
        sprite_name, frame = self._sprite_name_and_frame(sprites)
        sprite = sprites.get_sprite(sprite_name, frame, palette)
        if sprite_name in FELIX_HEAD_CENTER_X:
            left = center_x - FELIX_HEAD_CENTER_X[sprite_name]
        else:
            left = center_x - sprite.get_width() / 2
        top = camera.to_screen_y(feet_y, alpha) - sprite.get_height()
        screen.blit(sprite, (round(left), top))

    def _draw_hit_frame(self, screen, sprites, camera, palette, center_x, feet_y, alpha):
        sprite = sprites.get_frame(self._hit_frame_id(), palette)
        # The hit frames sit off-center in their atlas cells (frame 64's body is
        # 5px right of center), so center the visible art to keep Felix planted.
        left = center_x - sprite.get_bounding_rect().centerx
        top = camera.to_screen_y(feet_y, alpha) - sprite.get_height()
        screen.blit(sprite, (round(left), top))


def _frame_index_after(hold_ticks_per_frame, elapsed_ticks):
    """Frame index a play-once exe animation shows after elapsed ticks; it stops on the last frame."""
    for index, hold_ticks in enumerate(hold_ticks_per_frame):
        elapsed_ticks -= _frame_display_ticks(hold_ticks)
        if elapsed_ticks < 0:
            return index
    return len(hold_ticks_per_frame) - 1
