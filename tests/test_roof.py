import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

import roof_data as roof  # noqa: E402
from constants import GAME_HEIGHT, GAME_WIDTH  # noqa: E402
from entities.building import Building  # noqa: E402
from entities.sprite_node import SpriteNode  # noqa: E402
from input_handler import Action  # noqa: E402
from scene_manager import SceneManager  # noqa: E402
from scenes import high_score_scene  # noqa: E402
from scenes.game_over_scene import GameOverScene  # noqa: E402
from scenes.game_phases import (  # noqa: E402
    LEVEL_END_COUNTDOWN_TICKS, READY_MESSAGE_COLOUR, SCORE_POPUP_DELAY_TICKS,
    SCORE_POPUP_RISE_PX, LevelEndPhase, LevelStartPhase, PlayPhase,
)
from scenes.game_scene import GameScene  # noqa: E402
from scenes.high_score_scene import HighScoreScene  # noqa: E402
from scenes.roof_phases import GameEndPhase, RoofPhase  # noqa: E402
from scenes.title_scene import TitleScene  # noqa: E402
from entities.felix import FelixState  # noqa: E402
from level_config import get_level_config  # noqa: E402
from sprite_data import font_row_for_exe_colour  # noqa: E402

TICK_LIMIT = 5000


class MockInput:
    def __init__(self, just=()):
        self._just = set(just)

    def is_just_pressed(self, action):
        return action in self._just

    def is_pressed(self, action):
        return False

    def has_lost_focus(self):
        return False


class RecordingSound:
    """Stands in for SoundManager and logs every call in order."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, *args))
        return record


def make_game(seed=1, level=1):
    manager = SceneManager()
    game = GameScene(manager, rng=random.Random(seed))
    manager.push(game)
    game.sound = RecordingSound()
    if level != 1:
        game.start_level(level)
    return manager, game


def tick_until(game, condition, input_handler=None):
    for _ in range(TICK_LIMIT):
        if condition():
            return
        game.tick(input_handler or MockInput())
    raise AssertionError("condition never became true")


def reach_play(game):
    tick_until(game, lambda: isinstance(game.phase, PlayPhase))


def clear_level(game):
    """Fix every section through the normal flow, up to the start of the roof."""
    reach_play(game)
    for _ in range(game.building.section_count):
        for floor in game.building.section_floors():
            for cell in floor.cells:
                game.building.fix(cell)
        tick_until(game, lambda: not isinstance(game.phase, PlayPhase))
        tick_until(game, lambda: isinstance(game.phase, (PlayPhase, RoofPhase)))
    assert isinstance(game.phase, RoofPhase)
    return game.phase


def start_roof(game):
    """Jump straight to the roof (the level end wait is tested on its own)."""
    reach_play(game)
    game.phase = RoofPhase()
    return game.phase


def tick_roof_until(game, roof_phase, condition):
    tick_until(game, lambda: condition() or game.phase is not roof_phase)
    assert game.phase is roof_phase


def animation_ticks(anim_id):
    """Ticks from setting an animation until the script sees it finished: each frame shows hold + 1."""
    return sum(frame.hold + 1 for frame in roof.ROOF_ANIMATIONS[anim_id].frames)


def expected_roof_ticks():
    """The exe schedule (FUN_004039d0, FUN_00403a40, FUN_004044b0), step by step.

    Times are the tick on which each step completes; the next step runs from
    the following tick.
    """
    phase_1_start = roof.PHASE_0_TICKS
    hatch_open = phase_1_start + animation_ticks(roof.DOOR_ANIM)
    walk_moves = math.ceil((roof.NICELANDER_STOP_X - roof.NICELANDER_START_X) / roof.WALK_OUT_STEP_X)
    walked_out = hatch_open + walk_moves * roof.WALK_OUT_STEP_TICKS
    medal_done = walked_out + animation_ticks(roof.MEDAL_ANIM)
    pie_taken = medal_done + roof.PIE_WAIT_TICKS + animation_ticks(roof.PIE_GIVER_ANIM)
    pie_eaten = pie_taken + animation_ticks(roof.FELIX_ANIM_TAKES_PIE)
    frowning = pie_eaten + animation_ticks(roof.KISSER_ANIM) + roof.FROWN_WAIT_TICKS - 1
    leader_moves = math.ceil(roof.LEADER_STOP_OFFSET_X / roof.MARCH_STEP_X)
    lift_moves = math.ceil((roof.CARRY_STOP_OFFSET_X - roof.LEADER_STOP_OFFSET_X) / roof.MARCH_STEP_X)
    lifted = frowning + roof.MARCH_START_DELAY_TICKS + (leader_moves + lift_moves) * roof.MARCH_STEP_TICKS
    carry_moves = math.ceil((roof.THROW_STOP_OFFSET_X - roof.CARRY_STOP_OFFSET_X) / roof.MARCH_STEP_X)
    thrown = lifted + carry_moves * roof.MARCH_STEP_TICKS
    throw_start_x = roof.RALPH_CARRIED_X + carry_moves * roof.RALPH_CARRY_STEP_X
    flight_ticks = math.floor((roof.THROW_CUT_X - throw_start_x) / roof.THROW_VELOCITY[0]) + 1
    cut = thrown + flight_ticks
    fall_ticks = math.ceil((roof.LANDING_Y - roof.FALL_START_Y) / roof.FALL_SPEED)
    landed = cut + fall_ticks
    phase_2_start = landed + roof.AFTER_LANDING_TICKS + 1
    return phase_2_start + roof.PHASE_2_TICKS + 1


def test_roof_runs_on_the_exe_schedule_and_advances_keeping_score_and_lives():
    _, game = make_game()
    roof_phase = clear_level(game)
    game.felix.score = 4321
    game.felix.lives = 6
    roof_ticks = 0
    while game.phase is roof_phase:
        game.tick(MockInput())
        roof_ticks += 1
    assert roof_ticks == expected_roof_ticks()
    assert game.level == 2
    assert isinstance(game.phase, LevelStartPhase)
    assert (game.camera.scroll_x, game.camera.scroll_y) == (0, 0)
    assert (game.felix.score, game.felix.lives) == (4321, 6)


def test_level_end_waits_for_the_score_popup_then_the_countdown():
    _, game = make_game()
    reach_level_end_wait(game)
    wait_ticks = 0
    while isinstance(game.phase, LevelEndPhase):
        game.tick(MockInput())
        wait_ticks += 1
    assert isinstance(game.phase, RoofPhase)
    # The popup rises one pixel every other tick; the frame counter's parity picks
    # which of the two lengths, then the detection tick also counts down.
    rise_ticks = 2 * (SCORE_POPUP_RISE_PX + 1) - 1
    shortest = SCORE_POPUP_DELAY_TICKS - 1 + rise_ticks + LEVEL_END_COUNTDOWN_TICKS
    assert wait_ticks in (shortest, shortest + 1)


def test_no_hits_or_scoring_during_the_roof():
    _, game = make_game()
    roof_phase = start_roof(game)
    game.felix.score = 0
    lives_before = game.felix.lives
    broken_cell = game.building.cell(0, 0)
    broken_cell.top_pane = 3
    hitbox = game.felix.hitbox()
    game.bricks.spawn(hitbox.centerx, hitbox.bottom - 4)
    brick_before = [(brick.x, brick.y) for brick in game.bricks._bricks]
    felix_before = game.felix.world_pos()
    while True:
        game.tick(MockInput([Action.JUMP, Action.LEFT]))
        if game.phase is not roof_phase:
            break
        # Neither Felix nor the bricks tick: a brick on Felix would otherwise hit him,
        # and hammering would fix the broken window and score.
        assert [(brick.x, brick.y) for brick in game.bricks._bricks] == brick_before
        assert game.felix.world_pos() == felix_before
        assert (game.felix.lives, game.felix.score) == (lives_before, 0)
        assert broken_cell.is_broken
    assert game.level == 2


def reach_level_end_wait(game):
    """Clear every section through the normal flow; the last one enters LevelEndPhase."""
    reach_play(game)
    for _ in range(game.building.section_count - 1):
        for floor in game.building.section_floors():
            for cell in floor.cells:
                game.building.fix(cell)
        tick_until(game, lambda: not isinstance(game.phase, PlayPhase))
        tick_until(game, lambda: isinstance(game.phase, PlayPhase))
    for floor in game.building.section_floors():
        for cell in floor.cells:
            game.building.fix(cell)
    game.tick(MockInput())
    assert isinstance(game.phase, LevelEndPhase)
    return game.phase


def test_level_end_wait_keeps_felix_playable_and_clears_only_what_the_exe_clears():
    _, game = make_game(level=5)
    level_end = reach_level_end_wait(game)
    x_before, _ = game.felix.world_pos()
    for _ in range(20):
        game.tick(MockInput([Action.RIGHT] if game.felix.column < 4 else []))
    assert game.phase is level_end
    assert game.felix.world_pos()[0] != x_before
    assert game.felix.state != FelixState.CELEBRATING
    assert not game.hazards.birds
    assert ("stop_sound_index", 25) in game.sound.calls
    assert any(cell.has_sill_obstacle
               for floor in game.building.section_floors() for cell in floor.cells)


def test_level_end_clears_birds_but_keeps_drop_hazards():
    _, game = make_game(level=5)
    reach_play(game)
    game.hazards.start_section(game.building, get_level_config(game.level))
    game.hazards.request_drop(game.ralph, game.building, get_level_config(game.level))
    assert game.hazards.birds and game.hazards.drop_hazards
    game.phase = LevelEndPhase()
    game.tick(MockInput())
    assert not game.hazards.birds
    assert game.hazards.drop_hazards


def test_a_hit_during_the_wait_hits_felix_and_the_roof_cuts_it_short_without_a_life_lost():
    _, game = make_game()
    level_end = reach_level_end_wait(game)
    lives_before = game.felix.lives
    tick_until(game, lambda: level_end.countdown_ticks <= 10)
    hitbox = game.felix.hitbox()
    game.bricks.spawn(hitbox.centerx, hitbox.bottom - 4)
    game.tick(MockInput())
    assert game.felix.is_in_hit_sequence
    tick_until(game, lambda: isinstance(game.phase, RoofPhase))
    assert game.felix.lives == lives_before
    assert not game.felix.is_in_hit_sequence


def test_a_final_hit_during_the_wait_does_not_end_the_game():
    manager, game = make_game()
    level_end = reach_level_end_wait(game)
    game.felix.lives = 1
    tick_until(game, lambda: level_end.countdown_ticks <= 50)
    hitbox = game.felix.hitbox()
    game.bricks.spawn(hitbox.centerx, hitbox.bottom - 4)
    game.tick(MockInput())
    assert game.felix.state == FelixState.FINAL_HIT_ANIM
    tick_until(game, lambda: isinstance(game.phase, RoofPhase))
    assert manager.current is game
    roof_phase = game.phase
    tick_until(game, lambda: game.phase is not roof_phase)
    assert game.level == 2
    assert game.felix.lives == 1


def test_phase_0_shows_felix_with_the_hammer_raised_on_a_blank_world():
    _, game = make_game()
    roof_phase = start_roof(game)
    game.tick(MockInput())
    assert (game.camera.scroll_x, game.camera.scroll_y) == roof.PHASE_0_SCROLL
    assert (roof_phase.felix.x, roof_phase.felix.y) == roof.FELIX_PHASE_0_NODE[:2]
    assert roof_phase.felix.frame.frame_id == 31
    assert game.camera.to_screen_x(roof_phase.felix.x) == 120


def test_roof_y_matches_the_exe_rows_worked_out_by_hand():
    # Level 1 (9 floors): rows 7+7+6+7+6+7+6+6 = 52 below the roof, from row 40:
    # roof bottom row -12, roof height piece 9 = 20 rows, top row -32 -> y -256.
    assert Building(1, random.Random(1)).roof_top_y == -256
    # Level 3 (13 floors): 7+7 + 4 x (6+7) + 6+6 = 78 rows: bottom -38, top -58 -> -464.
    assert Building(3, random.Random(1)).roof_top_y == -464


def test_nicelanders_stay_hidden_until_past_the_hatch():
    _, game = make_game()
    roof_phase = start_roof(game)
    tick_roof_until(game, roof_phase, lambda: roof_phase.phase_number == 1 and roof_phase.step == 1)
    assert not any(node.is_visible for node in roof_phase.nicelanders)
    while roof_phase.step == 1:
        before = [(node.x, node.is_visible) for node in roof_phase.nicelanders]
        game.tick(MockInput())
        for node, (x_before, was_visible) in zip(roof_phase.nicelanders, before):
            assert node.is_visible == (was_visible or x_before > roof.NICELANDER_VISIBLE_AFTER_X)
    game.tick(MockInput())
    assert all(node.is_visible for node in roof_phase.nicelanders)
    assert [node.x for node in roof_phase.nicelanders] == [
        roof.NICELANDER_STOP_X + offset for offset in roof.WALK_OUT_OFFSETS_X]


def test_medal_finishes_then_felix_wears_it():
    _, game = make_game()
    roof_phase = start_roof(game)
    tick_roof_until(game, roof_phase, lambda: roof_phase.step == 2)
    assert roof_phase.medal.is_visible
    while roof_phase.step == 2:
        assert roof_phase.felix.frame.frame_id != 25
        game.tick(MockInput())
    assert roof_phase.medal.is_finished
    assert not roof_phase.medal.is_visible
    assert roof_phase.felix.frame.frame_id == 25


def test_ralph_is_thrown_at_2_minus_2_and_the_camera_cuts_past_x_304():
    _, game = make_game()
    roof_phase = start_roof(game)
    tick_roof_until(game, roof_phase, lambda: roof_phase.step == 8)
    assert (roof_phase.ralph_velocity_x, roof_phase.ralph_velocity_y) == roof.THROW_VELOCITY
    assert roof_phase.ralph_y == roof_phase.roof_y + roof.ACTOR_BELOW_ROOF_Y
    while roof_phase.step == 8:
        assert roof_phase.ralph_x <= roof.THROW_CUT_X
        assert game.camera.scroll_y != 0
        game.tick(MockInput())
    assert roof_phase.ralph_x > roof.THROW_CUT_X
    assert (game.camera.scroll_x, game.camera.scroll_y) == roof.GROUND_VIEW_SCROLL
    assert roof_phase.ralph_y == roof.FALL_START_Y
    assert roof_phase.ralph.frame.frame_id == 94


def test_ralph_lands_in_the_mud_at_317():
    _, game = make_game()
    roof_phase = start_roof(game)
    tick_roof_until(game, roof_phase, lambda: roof_phase.has_landed)
    assert (roof_phase.ralph.x, roof_phase.ralph.y) == (roof.FALL_X, 317)
    assert roof_phase.ralph.frame.frame_id == 96


def test_throw_fall_and_landing_sounds_play_in_order_and_the_fall_sound_stops():
    _, game = make_game()
    roof_phase = start_roof(game)
    tick_roof_until(game, roof_phase, lambda: roof_phase.has_landed)
    effects = [call for call in game.sound.calls
               if call[0] in ("play_sound_index", "stop_sound_index") and call[1] in (23, 19, 18)]
    assert effects == [("play_sound_index", 23), ("play_sound_index", 19),
                       ("stop_sound_index", 19), ("play_sound_index", 18)]


def test_roof_music_follows_the_three_phases():
    _, game = make_game()
    roof_phase = start_roof(game)
    calls_before_roof = len(game.sound.calls)
    while game.phase is roof_phase:
        game.tick(MockInput())
    roof_calls = game.sound.calls[calls_before_roof:]
    music = [call[1] for call in roof_calls if call[0] == "play_music_index"]
    assert music == [roof.PHASE_0_MUSIC, roof.PHASE_1_MUSIC, roof.PHASE_2_MUSIC]


def test_footstep_plays_on_every_fourth_march_move():
    _, game = make_game()
    roof_phase = start_roof(game)
    tick_roof_until(game, roof_phase, lambda: roof_phase.step == 8)
    footsteps = [call for call in game.sound.calls if call == ("play_sound_index", 27)]
    # Step 6: the leader alone to stop + 0x1b, then the group to stop + 0x50;
    # step 7: the carry to stop + 0x65. Each move is one footstep count.
    leader_moves = math.ceil(roof.LEADER_STOP_OFFSET_X / roof.MARCH_STEP_X)
    lift_moves = math.ceil((roof.CARRY_STOP_OFFSET_X - roof.LEADER_STOP_OFFSET_X)
                           / roof.MARCH_STEP_X)
    carry_moves = math.ceil((roof.THROW_STOP_OFFSET_X - roof.CARRY_STOP_OFFSET_X)
                            / roof.MARCH_STEP_X)
    march_moves = leader_moves + lift_moves + carry_moves
    # The counter starts at 0 and the sound plays on a move that finds it at 3.
    assert len(footsteps) == march_moves // roof.FOOTSTEP_EVERY_MOVES


def use_temporary_scores(tmp_path, monkeypatch, scores):
    scores_file = tmp_path / "scores.dat"
    monkeypatch.setattr(high_score_scene, "SCORES_FILE", str(scores_file))
    high_score_scene.save_scores(scores)
    return scores_file


def expected_game_end_ticks():
    columns = roof.GAME_END_FIRST_COLUMN - roof.GAME_END_LAST_COLUMN + 1
    return math.ceil(columns * roof.GAME_END_ROW_STEPS / roof.GAME_END_STEPS_PER_TICK)


def run_roof_into_game_end(game):
    roof_phase = start_roof(game)
    tick_until(game, lambda: game.phase is not roof_phase)
    assert isinstance(game.phase, GameEndPhase)


def test_level_39_ends_the_game_with_the_glyph_screen_then_initials_entry(tmp_path, monkeypatch):
    use_temporary_scores(tmp_path, monkeypatch, [{"name": "AAA", "score": 100}])
    manager, game = make_game(level=39)
    run_roof_into_game_end(game)
    game.felix.score = 50000
    game_end = game.phase
    end_ticks = 0
    while manager.current is game:
        game.tick(MockInput())
        end_ticks += 1
    assert end_ticks == expected_game_end_ticks()
    assert len(game_end.cells) == (roof.GAME_END_FIRST_COLUMN + 1) * roof.GAME_END_ROW_STEPS
    assert isinstance(manager.current, HighScoreScene)
    # Qualifying: START moves to the next initial instead of leaving for the title.
    manager.current.tick(MockInput([Action.START]))
    assert isinstance(manager.current, HighScoreScene)


def test_game_end_with_a_low_score_shows_the_table_and_leaves_scores_untouched(
        tmp_path, monkeypatch):
    saved = [{"name": name, "score": 90000 - index} for index, name in
             enumerate(("AAA", "BBB", "CCC", "DDD", "EEE"))]
    scores_file = use_temporary_scores(tmp_path, monkeypatch, saved)
    contents_before = scores_file.read_bytes()
    manager, game = make_game(level=39)
    run_roof_into_game_end(game)
    game.felix.score = 10
    tick_until(game, lambda: manager.current is not game)
    assert isinstance(manager.current, HighScoreScene)
    assert not isinstance(manager.current, GameOverScene)
    manager.current.tick(MockInput([Action.START]))
    assert isinstance(manager.current, TitleScene)
    assert scores_file.read_bytes() == contents_before


def test_n_pressed_during_play_ends_the_game_after_that_levels_roof(tmp_path, monkeypatch):
    use_temporary_scores(tmp_path, monkeypatch, [])
    manager, game = make_game()
    reach_play(game)
    game.tick(MockInput([Action.END_GAME]))
    roof_phase = clear_level(game)
    tick_until(game, lambda: game.phase is not roof_phase)
    assert isinstance(game.phase, GameEndPhase)
    assert game.level == 1
    tick_until(game, lambda: manager.current is not game)
    assert isinstance(manager.current, HighScoreScene)


def test_game_end_fill_writes_column_29_top_down_with_random_colours():
    _, game = make_game(level=39)
    run_roof_into_game_end(game)
    game.rng = random.Random(7)
    expected_rng = random.Random(7)
    expected_colours = [expected_rng.randrange(roof.GAME_END_COLOUR_COUNT) for _ in range(4)]
    game.tick(MockInput())
    assert game.phase.cells == {
        (29, row): (roof.GAME_END_GLYPHS[row], expected_colours[row]) for row in range(4)}
    surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
    game.draw(surface)


def test_ready_pause_shows_player_1_ready_at_the_exe_cell():
    _, game = make_game()
    tick_until(game, lambda: game.phase.is_ready_countdown)
    drawn = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
    game.phase.draw_overlay(game, drawn)
    expected = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
    text = game.font.render_text("PLAYER 1 READY",
                                 color_row=font_row_for_exe_colour(READY_MESSAGE_COLOUR))
    expected.blit(text, (8 * 8, 0x13 * 8))
    assert pygame.image.tostring(drawn, "RGB") == pygame.image.tostring(expected, "RGB")
    assert pygame.image.tostring(drawn, "RGB") != pygame.image.tostring(
        pygame.Surface((GAME_WIDTH, GAME_HEIGHT)), "RGB")


def test_sprite_node_frames_show_hold_plus_one_ticks_and_once_finishes():
    animation = roof.ROOF_ANIMATIONS[roof.FELIX_ANIM_TAKES_PIE]  # holds 10, 10, 10
    node = SpriteNode(animation, is_visible=True)
    frames_seen = []
    while not node.is_finished:
        node.tick()
        frames_seen.append(node.frame_index)
    assert frames_seen.count(0) == 10  # the first frame counts from the tick it was set
    assert frames_seen.count(1) == 11
    # Set on tick T (before its animation tick), the script sees "finished" on T + total.
    assert len(frames_seen) == animation_ticks(roof.FELIX_ANIM_TAKES_PIE)
    assert node.frame_index == len(animation.frames) - 1


def test_hidden_or_paused_nodes_do_not_animate():
    animation = roof.ROOF_ANIMATIONS[roof.DOOR_ANIM]
    hidden = SpriteNode(animation)
    paused = SpriteNode(animation, is_visible=True, is_paused=True)
    for _ in range(200):
        hidden.tick()
        paused.tick()
    assert (hidden.frame_index, paused.frame_index) == (0, 0)
