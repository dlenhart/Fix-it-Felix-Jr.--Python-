"""The roof ending (exe game state 6) and the game-end screen, as GamePhases.

RoofPhase replays FUN_00404870 (setup), FUN_004039d0 (phase 0, "YOU FIXED IT!"),
FUN_00403a40 (phase 1, a ten-step script) and FUN_004044b0 (phase 2, "LEVEL n
COMPLETE"). Felix and Ralph are scripted sprite nodes here: nothing is hit,
scored or controlled. GameEndPhase is FUN_0040af70's "11022012" screen.
"""
from __future__ import annotations

import struct
from typing import TYPE_CHECKING, Callable

import pygame

import roof_data as roof
from entities.sprite_node import SpriteNode
from scenes.game_phases import GamePhase, draw_exe_text

if TYPE_CHECKING:
    from scenes.game_scene import GameScene


def _to_float32(value: float) -> float:
    """Round to the exe's single-precision floats (Ralph's position and velocity are floats)."""
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _truncate(value: float) -> int:
    """FUN_00415b60 (_ftol2, CVTTSD2SI): truncate toward zero."""
    return int(value)


class RoofPhase(GamePhase):
    """Exe game state 6: the medal, the pie, and Ralph thrown off the roof.

    Per tick, as FUN_004089b0 / FUN_0040ed40 / FUN_004089d0 run it: the script,
    then every node's animation, then the step advance when the script marked
    the step done (so the next step runs on the next tick).
    """

    def __init__(self) -> None:
        self.has_started = False
        self.phase_number = 0  # DAT_00424304
        self.step = 0  # DAT_00424308
        self.counter = 0  # DAT_0042430c
        self.march_ticks = 0  # DAT_00424310
        self.is_step_done = False  # DAT_00424332
        self.has_kiss_started = False  # DAT_0042432c
        self.has_landed = False  # DAT_0042432e
        self.colour_step = 0  # DAT_00424328
        self.line_x = roof.NICELANDER_START_X  # DAT_00424314
        self.left_cloud_x = roof.LEFT_CLOUD_X
        self.right_cloud_x = roof.RIGHT_CLOUD_X
        self.ralph_x = 0.0  # DAT_004242dc
        self.ralph_y = 0.0  # DAT_004242e0
        self.ralph_velocity_x = 0.0  # DAT_004242d4
        self.ralph_velocity_y = 0.0  # DAT_004242d8
        self.is_level_complete = False  # DAT_00424330
        self.is_game_end = False  # DAT_004242a8
        self.roof_y = 0  # DAT_0042431c
        self._placement_count = 0
        self.felix = SpriteNode(roof.ROOF_ANIMATIONS[roof.FELIX_ANIM_HAMMER_RAISED])
        self.ralph = SpriteNode(roof.ROOF_ANIMATIONS[roof.RALPH_ANIM_STANDING])
        self.left_cloud = SpriteNode(roof.ROOF_ANIMATIONS[roof.CLOUD_ANIM])
        self.right_cloud = SpriteNode(roof.ROOF_ANIMATIONS[roof.CLOUD_ANIM])
        self.door = SpriteNode(roof.ROOF_ANIMATIONS[roof.DOOR_ANIM])
        self.medal = SpriteNode(roof.ROOF_ANIMATIONS[roof.MEDAL_ANIM])
        self.nicelanders = [
            SpriteNode(roof.ROOF_ANIMATIONS[roof.NICELANDER_FIRST_ANIM + index])
            for index in range(roof.NICELANDER_COUNT)
        ]
        self._steps: tuple[Callable[[GameScene], None], ...] = (
            self._step_hatch_opens,
            self._step_walk_out,
            self._step_award_medal,
            self._step_offer_pie,
            self._step_eat_pie,
            self._step_kiss_and_frown,
            self._step_lift_ralph,
            self._step_carry_to_edge,
            self._step_throw,
            self._step_fall_into_mud,
        )

    @property
    def nodes(self) -> list[SpriteNode]:
        return [self.felix, self.ralph, self.left_cloud, self.right_cloud, self.door,
                self.medal, *self.nicelanders]

    def tick(self, game: GameScene) -> GamePhase | None:
        if not self.has_started:
            self._set_up(game)
        self._run_script(game)
        if self.is_level_complete:
            self._advance_level(game)
            # start_level already installed the next level's LevelStartPhase.
            return None
        for node in self.nodes:
            node.tick()
        if self.is_step_done:
            self.step += 1
            self.is_step_done = False
        if self.is_game_end:
            return GameEndPhase(self)
        return None

    # --- setup and phase changes ---------------------------------------------

    def _set_up(self, game: GameScene) -> None:
        """FUN_00408fc0 case 6 then FUN_00404870."""
        self.has_started = True
        game.sound.stop_sound_index(roof.STATE_ENTRY_STOPPED_SOUND)
        self.roof_y = game.building.roof_top_y
        self._place(self.left_cloud, self.left_cloud_x,
                    self.roof_y - roof.LEFT_CLOUD_ABOVE_ROOF_Y, roof.LEFT_CLOUD_Z)
        self.left_cloud.is_visible = True
        self._place(self.right_cloud, self.right_cloud_x,
                    self.roof_y - roof.RIGHT_CLOUD_ABOVE_ROOF_Y, roof.RIGHT_CLOUD_Z)
        self.right_cloud.is_visible = True
        self._place(self.felix, *roof.FELIX_PHASE_0_NODE)
        self.felix.is_visible = True
        self._place(self.door, roof.DOOR_X, self.roof_y, roof.DOOR_Z)
        self.door.is_visible = True
        self.door.is_paused = True
        self._place(self.medal, roof.MEDAL_X, self.roof_y - roof.MEDAL_ABOVE_ROOF_Y, roof.MEDAL_Z)
        self.medal.is_paused = True
        # Ralph's node keeps its play position under the -240 camera, offscreen
        # (his x is at most 169); it shows again when phase 1 places it.
        game.sound.play_music_index(roof.PHASE_0_MUSIC, is_looping=False)
        game.camera.cut_to(*roof.PHASE_0_SCROLL)

    def _start_phase_1(self, game: GameScene) -> None:
        """FUN_00404610(1)."""
        game.sound.play_music_index(roof.PHASE_1_MUSIC, is_looping=False)
        self.phase_number = 1
        self.step = 0
        self.counter = 0
        game.camera.cut_to(0, roof.PHASE_1_ROOF_SCROLL_Y - self.roof_y)
        self.door.is_paused = False
        actor_y = self.roof_y + roof.ACTOR_BELOW_ROOF_Y
        self.felix.set_animation(roof.ROOF_ANIMATIONS[roof.FELIX_ANIM_STANDING])
        self._place(self.felix, roof.FELIX_PHASE_1_X, actor_y, roof.FELIX_PHASE_1_Z)
        self.ralph.set_animation(roof.ROOF_ANIMATIONS[roof.RALPH_ANIM_STANDING])
        self._place(self.ralph, roof.RALPH_PHASE_1_X, actor_y, roof.RALPH_Z)
        self.ralph.is_visible = True

    def _start_phase_2(self, game: GameScene) -> None:
        """FUN_00404610(2)."""
        game.sound.play_music_index(roof.PHASE_2_MUSIC, is_looping=False)
        self.counter = 0
        self.phase_number = 2

    def _advance_level(self, game: GameScene) -> None:
        """FUN_004089b0 once DAT_00424330 is set: the next level, score and lives kept."""
        game.start_level(game.level + 1)

    # --- the script (FUN_004047f0) -------------------------------------------

    def _run_script(self, game: GameScene) -> None:
        if self.phase_number == 1:
            for nicelander in self.nicelanders:
                if nicelander.x > roof.NICELANDER_VISIBLE_AFTER_X:
                    nicelander.is_visible = True
        # FUN_004047f0 also skips the script while DAT_00424332 is set; tick()
        # clears the flag in the tick that sets it, so that guard never fires here.
        if self.phase_number == 0:
            self._tick_phase_0(game)
        elif self.phase_number == 1:
            self._steps[self.step](game)
        else:
            self._tick_phase_2(game)

    def _tick_phase_0(self, game: GameScene) -> None:
        """FUN_004039d0: 180 ticks of "YOU FIXED IT!" cycling colours."""
        self.counter += 1
        if self.counter >= roof.PHASE_0_TICKS:
            self._start_phase_1(game)
            return
        if game.frame_counter & roof.PHASE_0_COLOUR_FRAME_MASK == 0:
            self.colour_step += 1
            if self.colour_step >= roof.PHASE_0_COLOUR_STEPS:
                self.colour_step = 0

    def _tick_phase_2(self, game: GameScene) -> None:
        """FUN_004044b0: 180 ticks, then the next level, or the end on the 39th level or after 'N'.

        The exe compares the 0-based level index (DAT_00421808) with 0x26; our
        level is 1-based.
        """
        self.counter += 1
        if self.counter <= roof.PHASE_2_TICKS:
            return
        level_index = game.level - 1
        if level_index != roof.GAME_END_LEVEL_INDEX and not game.is_end_game_requested:
            self.is_level_complete = True
            return
        self.is_game_end = True

    def _step_hatch_opens(self, game: GameScene) -> None:
        if not self.door.is_finished:
            return
        self.felix.set_animation(roof.ROOF_ANIMATIONS[roof.FELIX_ANIM_LOOKS_AT_DOOR])
        self.counter = 0
        self.is_step_done = True

    def _step_walk_out(self, game: GameScene) -> None:
        self.counter += 1
        if self.counter < roof.WALK_OUT_STEP_TICKS:
            return
        self.line_x += roof.WALK_OUT_STEP_X
        self.counter = 0
        if self.line_x >= roof.NICELANDER_STOP_X:
            self.line_x = roof.NICELANDER_STOP_X
            self.felix.set_animation(roof.ROOF_ANIMATIONS[roof.FELIX_ANIM_STANDING])
            self.medal.is_visible = True
            self.medal.is_paused = False
            self.is_step_done = True
        self._place_nicelanders(roof.WALK_OUT_OFFSETS_X)

    def _step_award_medal(self, game: GameScene) -> None:
        self.counter += 1
        if self.counter >= roof.CLOUD_STEP_TICKS:
            self.right_cloud_x += roof.CLOUD_STEP_X
            self.left_cloud_x -= roof.CLOUD_STEP_X
            self.counter = 0
            self._place(self.left_cloud, self.left_cloud_x,
                        self.roof_y - roof.LEFT_CLOUD_ABOVE_ROOF_Y, roof.LEFT_CLOUD_Z)
            self._place(self.right_cloud, self.right_cloud_x,
                        self.roof_y - roof.RIGHT_CLOUD_ABOVE_ROOF_Y, roof.RIGHT_CLOUD_Z)
        if not self.medal.is_finished:
            return
        self.medal.is_visible = False
        self.felix.set_animation(roof.ROOF_ANIMATIONS[roof.FELIX_ANIM_WEARING_MEDAL])
        self.counter = 0
        self.is_step_done = True

    def _step_offer_pie(self, game: GameScene) -> None:
        pie_giver = self.nicelanders[roof.PIE_GIVER_INDEX]
        if self.counter < roof.PIE_WAIT_TICKS:
            self.counter += 1
            if self.counter >= roof.PIE_WAIT_TICKS:
                pie_giver.set_animation(roof.ROOF_ANIMATIONS[roof.PIE_GIVER_ANIM])
            return
        if not pie_giver.is_finished:
            return
        self.felix.set_animation(roof.ROOF_ANIMATIONS[roof.FELIX_ANIM_TAKES_PIE])
        self.is_step_done = True

    def _step_eat_pie(self, game: GameScene) -> None:
        if not self.felix.is_finished:
            return
        self.felix.set_animation(roof.ROOF_ANIMATIONS[roof.FELIX_ANIM_EATS_PIE])
        self.nicelanders[roof.PIE_GIVER_INDEX].set_animation(
            roof.ROOF_ANIMATIONS[roof.PIE_GIVER_IDLE_ANIM])
        self.nicelanders[roof.KISSER_INDEX].set_animation(roof.ROOF_ANIMATIONS[roof.KISSER_ANIM])
        self.has_kiss_started = False
        self.counter = 0
        self.is_step_done = True

    def _step_kiss_and_frown(self, game: GameScene) -> None:
        kisser = self.nicelanders[roof.KISSER_INDEX]
        if not kisser.is_finished:
            if not self.has_kiss_started and kisser.frame_index == roof.KISS_FRAME_INDEX:
                self.felix.set_animation(roof.ROOF_ANIMATIONS[roof.FELIX_ANIM_KISSED])
                game.sound.play_sound_index(roof.KISS_SOUND)
                self.has_kiss_started = True
            return
        self.counter += 1
        if self.counter < roof.FROWN_WAIT_TICKS:
            return
        for index, nicelander in enumerate(self.nicelanders):
            nicelander.set_animation(roof.ROOF_ANIMATIONS[roof.FROWN_FIRST_ANIM + index])
        self.counter = 0
        self.march_ticks = 0
        self.is_step_done = True

    def _step_lift_ralph(self, game: GameScene) -> None:
        """The first Nicelander walks to Ralph, then all five march under him."""
        self.counter += 1
        if self.counter <= roof.MARCH_START_DELAY_TICKS:
            return
        if not self._is_march_move_tick():
            return
        self._step_footstep(game)
        leader_stop_x = roof.NICELANDER_STOP_X + roof.LEADER_STOP_OFFSET_X
        if self.line_x < leader_stop_x:
            self.line_x = min(self.line_x + roof.MARCH_STEP_X, leader_stop_x)
            self._place(self.nicelanders[0], self.line_x, self._actor_y, roof.NICELANDER_Z)
            return
        carry_stop_x = roof.NICELANDER_STOP_X + roof.CARRY_STOP_OFFSET_X
        self.line_x += roof.MARCH_STEP_X
        if self.line_x >= carry_stop_x:
            self.line_x = carry_stop_x
            self.ralph_x = roof.RALPH_CARRIED_X
            self.ralph.set_animation(roof.ROOF_ANIMATIONS[roof.RALPH_ANIM_CARRIED])
            self._place(self.ralph, _truncate(self.ralph_x), self._actor_y, roof.RALPH_Z)
            self.is_step_done = True
        self._place_nicelanders(roof.MARCH_OFFSETS_X)

    def _step_carry_to_edge(self, game: GameScene) -> None:
        """Ralph, the Nicelanders and the camera move right together; at the edge, the throw."""
        if not self._is_march_move_tick():
            return
        self.ralph_x = _to_float32(self.ralph_x + roof.RALPH_CARRY_STEP_X)
        game.camera.scroll_x += roof.CAMERA_CARRY_STEP_X
        self._step_footstep(game)
        throw_x = roof.NICELANDER_STOP_X + roof.THROW_STOP_OFFSET_X
        self.line_x += roof.MARCH_STEP_X
        if self.line_x >= throw_x:
            self.line_x = throw_x
            self.ralph_velocity_x, self.ralph_velocity_y = roof.THROW_VELOCITY
            self.ralph_y = float(self._actor_y)
            self.is_step_done = True
            game.sound.play_sound_index(roof.THROW_SOUND)
        self._place(self.ralph, _truncate(self.ralph_x), self._actor_y, roof.RALPH_Z)
        self._place_nicelanders(roof.MARCH_OFFSETS_X)

    def _step_throw(self, game: GameScene) -> None:
        """A ballistic arc; once past x 304 the camera cuts to the ground and Ralph tumbles down."""
        self.ralph_x = _to_float32(self.ralph_x + self.ralph_velocity_x)
        self.ralph_y = _to_float32(self.ralph_y + self.ralph_velocity_y)
        self.ralph_velocity_y = _to_float32(self.ralph_velocity_y + roof.THROW_GRAVITY)
        if self.ralph_x > roof.THROW_CUT_X:
            self.ralph_y = roof.FALL_START_Y
            game.camera.cut_to(*roof.GROUND_VIEW_SCROLL)
            self.ralph.set_animation(roof.ROOF_ANIMATIONS[roof.RALPH_ANIM_TUMBLING])
            self._place(self.ralph, roof.FALL_X, _truncate(self.ralph_y), roof.RALPH_Z)
            self.counter = 0
            self.has_landed = False
            self.is_step_done = True
            game.sound.play_sound_index(roof.FALL_SOUND)
        # The exe re-places Ralph from his floats even on the cut tick (x 305 for one tick).
        self._place(self.ralph, _truncate(self.ralph_x), _truncate(self.ralph_y), roof.RALPH_Z)

    def _step_fall_into_mud(self, game: GameScene) -> None:
        if self.has_landed:
            self.counter += 1
            if self.counter > roof.AFTER_LANDING_TICKS:
                self._start_phase_2(game)
            return
        self.ralph_y = _to_float32(self.ralph_y + roof.FALL_SPEED)
        if self.ralph_y >= roof.LANDING_Y:
            self.ralph_y = roof.LANDING_Y
            self.has_landed = True
            self.ralph.set_animation(roof.ROOF_ANIMATIONS[roof.RALPH_ANIM_LANDS])
            game.sound.stop_sound_index(roof.FALL_SOUND)
            game.sound.play_sound_index(roof.LANDING_SOUND)
        self._place(self.ralph, roof.FALL_X, _truncate(self.ralph_y), roof.RALPH_Z)

    # --- helpers ---------------------------------------------------------------

    @property
    def _actor_y(self) -> int:
        return self.roof_y + roof.ACTOR_BELOW_ROOF_Y

    def _place(self, node: SpriteNode, x: int, y: int, z: int) -> None:
        self._placement_count += 1
        node.place(x, y, z, self._placement_count)

    def _place_nicelanders(self, offsets_x: tuple[int, ...]) -> None:
        for nicelander, offset_x in zip(self.nicelanders, offsets_x, strict=True):
            self._place(nicelander, self.line_x + offset_x, self._actor_y, roof.NICELANDER_Z)

    def _is_march_move_tick(self) -> bool:
        self.march_ticks += 1
        if self.march_ticks < roof.MARCH_STEP_TICKS:
            return False
        self.march_ticks = 0
        return True

    @staticmethod
    def _step_footstep(game: GameScene) -> None:
        """DAT_0041a238 counts moves; every 4th plays the footstep."""
        previous_count = game.roof_footstep_counter
        game.roof_footstep_counter = previous_count + 1
        if previous_count < roof.FOOTSTEP_EVERY_MOVES - 1:
            return
        game.sound.play_sound_index(roof.FOOTSTEP_SOUND)
        game.roof_footstep_counter = 0

    # --- drawing (FUN_004089d0) --------------------------------------------------

    def draw_world(self, game: GameScene, screen: pygame.Surface, alpha: float) -> None:
        """The building, the phase's text, then the nodes by depth.

        Drawn at the latest tick (no interpolation): the exe moves the camera and
        the nodes in whole-pixel steps together, and blending only the camera
        would make the carried Ralph shimmer.
        """
        game.building.draw_street(screen, game.sprites, game.camera, game.palette)
        game.building.draw(screen, game.sprites, game.camera, game.palette)
        self._draw_phase_text(game, screen)
        for node in sorted(self.nodes, key=lambda node: (node.z, node.placement_order)):
            node.draw(screen, game.sprites, game.camera, game.palette)

    def _draw_phase_text(self, game: GameScene, screen: pygame.Surface) -> None:
        if self.phase_number == 0:
            draw_exe_text(game, screen, roof.PHASE_0_MESSAGE, roof.PHASE_0_MESSAGE_COLUMN,
                          roof.PHASE_0_MESSAGE_ROW,
                          roof.PHASE_0_MESSAGE_FIRST_COLOUR + self.colour_step)
            return
        if self.phase_number == 2:
            self._draw_level_complete(game, screen)

    def _draw_level_complete(self, game: GameScene, screen: pygame.Surface) -> None:
        """FUN_00404500: "LEVEL n" and "COMPLETE" placed from Ralph's floats, over the mud."""
        column = roof.PHASE_2_COLUMN_BASE - _truncate(self.ralph_x * roof.PHASE_2_COLUMN_SCALE)
        level_row = _truncate(self.ralph_y * roof.PHASE_2_ROW_SCALE - roof.PHASE_2_LEVEL_ROW_OFFSET)
        complete_row = _truncate(
            self.ralph_y * roof.PHASE_2_ROW_SCALE - roof.PHASE_2_COMPLETE_ROW_OFFSET)
        level_index = game.level - 1
        level_offset_x = (roof.HALF_CELL_X
                          if level_index < roof.PHASE_2_HALF_CELL_LEVEL_INDEX_LIMIT else 0)
        draw_exe_text(game, screen, roof.PHASE_2_LEVEL_FORMAT.format(game.level), column,
                      level_row, roof.PHASE_2_COLOUR, offset_x=level_offset_x)
        draw_exe_text(game, screen, roof.PHASE_2_COMPLETE, column, complete_row,
                      roof.PHASE_2_COLOUR)


class GameEndPhase(GamePhase):
    """FUN_0040af70 with DAT_004242a8 set: the "11022012" screen over the frozen roof.

    Each tick writes 4 cells of a 30x40 text grid, down a column from row 0 to
    40 (row 40 is never drawn), starting at column 29 and moving left. Columns
    below 0 only count rows, a pause, until the column drops below -40.
    Nothing else ticks: the roof's last frame stays drawn underneath.
    """

    def __init__(self, roof_phase: RoofPhase) -> None:
        self.roof_phase = roof_phase
        self.column = roof.GAME_END_FIRST_COLUMN  # DAT_00424294
        self.row = 0  # DAT_00424298
        self.glyph_index = 0  # DAT_00424290
        self.cells: dict[tuple[int, int], tuple[str, int]] = {}
        self.is_finished = False

    def tick(self, game: GameScene) -> GamePhase | None:
        if self.is_finished:
            return None
        for _ in range(roof.GAME_END_STEPS_PER_TICK):
            if self.column >= 0:
                exe_colour = game.rng.randrange(roof.GAME_END_COLOUR_COUNT)
                self.cells[(self.column, self.row)] = (roof.GAME_END_GLYPHS[self.glyph_index],
                                                       exe_colour)
            self.glyph_index = (self.glyph_index + 1) % len(roof.GAME_END_GLYPHS)
            is_column_done = self.row >= roof.GAME_END_ROW_STEPS - 1
            self.row += 1
            if not is_column_done:
                continue
            self.column -= 1
            self.row = 0
            if self.column < roof.GAME_END_LAST_COLUMN:
                self.is_finished = True
                game.finish_game_end_screen()
                return None
        return None

    def draw_world(self, game: GameScene, screen: pygame.Surface, alpha: float) -> None:
        self.roof_phase.draw_world(game, screen, alpha)

    def draw_overlay(self, game: GameScene, screen: pygame.Surface) -> None:
        """FUN_0040f2e0 draws the text grid over everything, HUD included."""
        for (column, row), (glyph, exe_colour) in self.cells.items():
            if column >= roof.TEXT_GRID_COLUMNS or row >= roof.TEXT_GRID_ROWS:
                continue
            cell = game.font.render_opaque_glyph_cell(glyph, exe_colour)
            screen.blit(cell, (column * roof.TEXT_CELL_SIZE, row * roof.TEXT_CELL_SIZE))
