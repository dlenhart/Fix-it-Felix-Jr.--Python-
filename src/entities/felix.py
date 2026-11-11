import math

import pygame

from audio.sound_sink import SILENT_SOUND, SoundSink
from constants.building import STREET_Y
from constants.felix import (
    FELIX_BUMP_POINT_ABOVE_FEET, FELIX_FALL_MAX_SPEED, FELIX_FINAL_HIT_SETTLE_FRAME_INDEX,
    FELIX_GAME_OVER_DELAY_TICKS, FELIX_HAMMER_START_OFFSET, FELIX_HIT_FALL_BELOW_STREET,
    FELIX_HIT_FALL_GRAVITY, FELIX_HORIZONTAL_ACCEL, FELIX_MAX_HORIZONTAL_SPEED,
    FELIX_RESPAWN_DELAY_TICKS, FELIX_VERTICAL_MOVE_RATE, HAMMER_ANIM_RATE,
    HAMMER_EXTENDED_TICKS, HITBOX_HEIGHT, HITBOX_WIDTH, INITIAL_LIVES,
    INVULNERABLE_BLINK_TICKS, INVULNERABLE_TICKS, SPRITE_FRAME_HOLD_TICKS,
)
from constants.grid import (
    CENTER_COLUMN, COLUMN_COUNT, FLOORS_PER_SECTION, RESPAWN_COLUMN, RESPAWN_LOCAL_ROW,
)
from constants.scoring import BONUS_LIFE_THRESHOLD
from constants.sounds import FINAL_HIT_MUSIC, SECTION_CLEAR_JINGLE
from controls.action import Action
from entities.events import FelixEvents
from entities.felix_state import HIDDEN_STATES, HIT_SEQUENCE_STATES, FelixState
from exe_data.sprite_data import (
    FELIX_FINAL_HIT_FRAMES, FELIX_FINAL_HIT_FRAME_HOLD_TICKS, FELIX_HEAD_CENTER_X,
    FELIX_HIT_ANIM_TICKS, FELIX_HIT_FRAMES_LEFT, FELIX_HIT_FRAMES_RIGHT,
    FELIX_HIT_FRAME_HOLD_TICKS,
)
from graphics.animation import frame_display_ticks


def _hitbox_at(x, feet_y):
    return pygame.Rect(
        round(x - HITBOX_WIDTH / 2),
        round(feet_y - HITBOX_HEIGHT),
        HITBOX_WIDTH,
        HITBOX_HEIGHT,
    )


class Felix:
    """Felix on the active section: world-space position (center x, feet y)."""

    def __init__(self):
        self.column = RESPAWN_COLUMN
        self.local_row = RESPAWN_LOCAL_ROW
        self.state = FelixState.IDLE
        self.facing_right = True
        self.score = 0
        self.lives = INITIAL_LIVES

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

    def add_score(self, points, sound: SoundSink = SILENT_SOUND):
        """Add points; each multiple of 5000 crossed is a bonus life.

        [EXE] FUN_004063d0 stops sound 22 (the section jingle) and plays sound 25.
        """
        self.score += points
        while self.score >= self._next_bonus_at:
            self.lives += 1
            self._next_bonus_at += BONUS_LIFE_THRESHOLD
            sound.stop_sound_index(SECTION_CLEAR_JINGLE)
            sound.play_sfx("bonus_life")

    def hit(self, sound: SoundSink = SILENT_SOUND):
        """Start the hit sequence (FUN_0040ca00). Returns False if it did not land.

        The life is lost at the respawn, as in the exe. On the last life Felix
        never respawns, so lives drop to 0 at the hit: the HUD shows no life
        during the death sequence (the user's call; the exe's HUD timing is
        not decoded).
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
        self.lives = 0
        self.state = FelixState.FINAL_HIT_ANIM
        sound.play_music_index(FINAL_HIT_MUSIC, is_looping=False)
        return True

    def cancel_hit_sequence(self):
        """The roof ending cut a hit short: no life is lost.

        [EXE] State 6 stops ticking Felix (FUN_0040ccf0), so FUN_0040c1a0 never
        reaches the respawn that takes the life, and the level advance
        (FUN_004089b0 -> FUN_0040cf80) resets his handler. The spare-life count
        DAT_00421804 is untouched, so a final hit leaves him on his last life
        (our lives 1; hit() showed 0 for the death sequence).
        """
        if self.state in (FelixState.FINAL_HIT_ANIM, FelixState.FINAL_HIT_HOLD):
            self.lives = 1
        if self.is_in_hit_sequence:
            self.state = FelixState.IDLE

    def end_invulnerability(self):
        """Drop the pie's invulnerability early (FUN_0040cac0 on entering a new section)."""
        self._invulnerable_ticks_remaining = 0

    def activate_invulnerability(self, sound: SoundSink = SILENT_SOUND):
        """Felix took the pie: FUN_0040b5e0 plays sound 2 and the sound 24 tune."""
        self._invulnerable_ticks_remaining = INVULNERABLE_TICKS
        sound.play_sfx("pie_pickup")
        sound.play_sfx("invulnerable_tune")

    def world_pos(self, alpha=1.0):
        """Interpolated (center x, feet y) in world coordinates."""
        x = self._prev_pos_x + (self._pos_x - self._prev_pos_x) * alpha
        y = self._prev_pos_y + (self._pos_y - self._prev_pos_y) * alpha
        return x, y

    def hitbox(self):
        """World-space collision rect, centered on the feet x and standing on the feet y."""
        return _hitbox_at(self._pos_x, self._pos_y)

    def tick(self, input_handler, building, sound: SoundSink = SILENT_SOUND,
             is_spot_threatened=None) -> FelixEvents:
        """Advance one tick and report what happened: a window fixed, a respawn.

        is_spot_threatened(hitbox) -> bool, if given, steers the respawn away
        from spots a brick is falling toward; without it Felix respawns in place.
        Raises RuntimeError if place_at was never called.
        """
        if not self._is_placed:
            raise RuntimeError("Felix.tick before place_at: he has no position on the building")
        events = FelixEvents()
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
            self._tick_jumping(building, sound)
        elif self.state == FelixState.JUMP_BUMPED:
            self._tick_jump_bumped(building)
        elif self.state == FelixState.HAMMERING:
            self._tick_hammering()
        elif self.state == FelixState.HAMMER_EXTENDED:
            self._tick_hammer_extended(building, sound, events)
        elif self.state == FelixState.HIT_ANIM:
            self._tick_hit_anim()
        elif self.state == FelixState.HIT_FALL:
            self._tick_hit_fall()
        elif self.state == FelixState.HIT_RESPAWN_WAIT:
            self._tick_hit_respawn_wait(building, is_spot_threatened, events)
        elif self.state == FelixState.FINAL_HIT_ANIM:
            self._tick_final_hit_anim()
        elif self.state == FelixState.FINAL_HIT_HOLD:
            self._tick_final_hit_hold()
        return events

    def _tick_idle(self, input_handler, building, sound):
        self._snap_to_anchor(building)

        if input_handler.is_just_pressed(Action.JUMP):
            self.state = FelixState.HAMMERING
            self._state_ticks = 0
            self._hammer_offset = FELIX_HAMMER_START_OFFSET
            # FUN_0040b510: the swing plays sound 1 only at a broken window.
            if self._current_cell(building).is_broken:
                sound.play_sfx("hammer_swing")
            return

        if input_handler.is_just_pressed(Action.LEFT):
            self._start_walk(-1)
        elif input_handler.is_just_pressed(Action.RIGHT):
            self._start_walk(1)
        elif input_handler.is_just_pressed(Action.UP):
            self._start_jump(1, building, sound)
        elif input_handler.is_just_pressed(Action.DOWN):
            self._start_jump(-1, building, sound)

    def _start_walk(self, direction):
        # The exe's walk start (FUN_0040c3d0 case 3) plays no sound.
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

    def _start_jump(self, row_step, building, sound):
        target_row = self.local_row + row_step
        # [ASSUMED] Jumping up from the top floor of a section is refused (spec); not decoded.
        if not 0 <= target_row < FLOORS_PER_SECTION:
            return
        # FUN_0040b5e0 starts the drop down (state 6) only when the cell has no
        # obstacle (cell+0x2c == 0). An obstacle above doesn't stop the jump up;
        # it bumps it (_tick_jumping).
        if row_step < 0 and self._current_cell(building).has_sill_obstacle:
            return
        self._target_row = target_row
        self.state = FelixState.JUMPING
        self._state_ticks = 0
        sound.play_sfx("jump" if row_step > 0 else "drop_down")

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

    def _tick_jumping(self, building, sound):
        # [ASSUMED] Straight line at FELIX_VERTICAL_MOVE_RATE to the target sill; the
        # exe's FUN_0040bea0 is a gravity jump (about 60 px high), arc not modelled.
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
        if self._target_row > self.local_row:
            self._bump_on_obstacle_above(building, sound)

    def _bump_on_obstacle_above(self, building, sound):
        """FUN_0040bea0: a rising jump that reaches the obstacle above bumps and falls back.

        The exe tests after each tick's move. It also tests the obstacle two
        floors up, which its jump (about 60 px high) can reach; ours stops at the
        target sill, so that one is out of reach and not modelled.
        """
        cell_above = building.cell(self._target_row, self.column)
        if not cell_above.has_sill_obstacle:
            return
        _, obstacle_y = building.sill_obstacle_node(cell_above)
        if self._pos_y - FELIX_BUMP_POINT_ABOVE_FEET > obstacle_y:
            return
        cell_above.bump_sill_obstacle()
        sound.play_sfx("obstacle_bump")  # FUN_004097d0: sound 6
        self._vel_y = 0.0
        self.state = FelixState.JUMP_BUMPED

    def _tick_jump_bumped(self, building):
        # FUN_0040c0d0 (state 9): move, land on the sill he falls through (his own,
        # since he never left the cell), else fall faster.
        self._pos_y += self._vel_y
        _, sill_y = self._anchor(building, self.local_row, self.column)
        if self._pos_y >= sill_y:
            self._snap_to_anchor(building)
            self._vel_y = 0.0
            self.state = FelixState.IDLE
            return
        self._vel_y = min(self._vel_y + FELIX_HIT_FALL_GRAVITY, FELIX_FALL_MAX_SPEED)

    def _tick_hammering(self):
        # The exe's hammer anim plays no sound of its own; the swing's sound is at the press.
        self._state_ticks += 1
        self._hammer_offset += HAMMER_ANIM_RATE
        if self._hammer_offset < 0.0:
            return
        self.state = FelixState.HAMMER_EXTENDED
        self._state_ticks = 0

    def _tick_hammer_extended(self, building, sound, events):
        # The fix (FUN_0040bc80 -> FUN_00409a70) plays no sound either.
        self._state_ticks += 1
        if self._state_ticks < HAMMER_EXTENDED_TICKS:
            return
        cell = self._current_cell(building)
        points = building.fix(cell)
        self.state = FelixState.IDLE
        if not points:
            return
        events.fixed_cell = cell
        events.fixed_points = points
        self.add_score(points, sound)

    def _tick_hit_anim(self):
        self._hit_anim_ticks += 1
        if self._hit_anim_ticks < FELIX_HIT_ANIM_TICKS:
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

    def _tick_hit_respawn_wait(self, building, is_spot_threatened, events):
        self._state_ticks -= 1
        if self._state_ticks > 0:
            return
        self.lives -= 1
        column = self._choose_respawn_column(building, is_spot_threatened)
        self.place_at(self.local_row, column, building)
        events.has_respawned = True

    def _choose_respawn_column(self, building, is_spot_threatened):
        """Pick the nearest column on this floor that no brick is falling toward.

        [USER] deviation: the exe (FUN_0040c1a0) always respawns on the hit cell.
        Also treating a drop-hazard as a threat is [ASSUMED] (Ruling 21: neither
        the exe nor a user ruling).
        The bricks are frozen during the hit, so one above that cell could hit
        him again right away. Nearest first, then toward the center column; his
        own column if every spot is threatened. He starts from the cell he was
        on, not the one a walk or jump was heading for.
        """
        if is_spot_threatened is None:
            return self.column
        candidates = sorted(
            range(COLUMN_COUNT),
            key=lambda column: (
                abs(column - self.column),
                abs(column - CENTER_COLUMN),
                column,
            ),
        )
        for column in candidates:
            x, feet_y = self._anchor(building, self.local_row, column)
            if not is_spot_threatened(_hitbox_at(x, feet_y)):
                return column
        return self.column

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
        self.state = FelixState.GAME_OVER

    @staticmethod
    def _anchor(building, local_row, column):
        """Standing point: the cell's center x on its sill (the exe's cell+0x74, FUN_0040c0d0)."""
        cell = building.cell(local_row, column)
        return cell.center_x, float(building.sill_y(cell))

    def _current_cell(self, building):
        return building.cell(self.local_row, self.column)

    def _snap_to_anchor(self, building):
        self._pos_x, self._pos_y = self._anchor(building, self.local_row, self.column)

    @property
    def hit_frame_id(self):
        """Exe frame id the hit or final-hit animation is showing right now."""
        return self._hit_frame_id()

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
        if self.state in (FelixState.WALK_HORIZONTAL, FelixState.JUMPING, FelixState.JUMP_BUMPED):
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
        screen.blit(sprite, (camera.to_screen_x(round(left), alpha),
                             _sprite_top(camera, feet_y, alpha, sprite)))

    def _draw_hit_frame(self, screen, sprites, camera, palette, center_x, feet_y, alpha):
        sprite = sprites.get_frame(self._hit_frame_id(), palette)
        # The hit frames sit off-center in their atlas cells (frame 64's body is
        # 5px right of center), so center the visible art to keep Felix planted.
        left = center_x - sprite.get_bounding_rect().centerx
        screen.blit(sprite, (camera.to_screen_x(round(left), alpha),
                             _sprite_top(camera, feet_y, alpha, sprite)))


def _sprite_top(camera, feet_y, alpha, sprite):
    """Screen y of a Felix frame's top: its last row sits on feet_y.

    Felix's anims use origin y 47 on 48-tall frames (anims 4, 9, 10, 15), so
    the exe draws the frame's bottom row on the node's y, the sill.
    """
    return camera.to_screen_y(feet_y, alpha) - (sprite.get_height() - 1)


def _frame_index_after(hold_ticks_per_frame, elapsed_ticks):
    """Frame index a play-once exe animation shows after elapsed ticks; it stops on the last frame."""
    for index, hold_ticks in enumerate(hold_ticks_per_frame):
        elapsed_ticks -= frame_display_ticks(hold_ticks)
        if elapsed_ticks < 0:
            return index
    return len(hold_ticks_per_frame) - 1
