import os
import random

import pygame

from audio.sound_manager import SoundManager
from constants.display import BLACK, GAME_HEIGHT, GAME_WIDTH
from constants.grid import RESPAWN_COLUMN, RESPAWN_LOCAL_ROW
from constants.levels import PALETTE_COUNT, START_LEVEL_ENVIRONMENT_VARIABLE
from constants.sounds import GAMEPLAY_MUSIC
from controls.action import Action
from core.camera import Camera
from core.scene import Scene
from entities.brick_field import BrickField
from entities.felix import Felix
from entities.hazard_field import HazardField
from entities.nicelander_director import NicelanderDirector
from entities.ralph import Ralph
from graphics.font_renderer import FontRenderer
from graphics.sprite_sheet import SpriteSheet
from graphics.text_layout import draw_centered_text
from scenes.game.game_session import GameSession
from scenes.game.hud import Hud
from scenes.game.phases.game_phase import GamePhase
from scenes.game.phases.level_start_phase import LevelStartPhase
from scenes.game.phases.play_phase import PlayPhase
from world.building import Building
from world.level_config import get_level_config


def start_level_from_environment() -> int:
    """Return the level a new game starts on: 1, or FELIX_START_LEVEL when set.

    A dev shortcut for reaching later levels, e.g. FELIX_START_LEVEL=5 python3 src/main.py.
    Raises ValueError when the value is not an integer or is below 1.
    """
    raw_level = os.environ.get(START_LEVEL_ENVIRONMENT_VARIABLE)
    if raw_level is None:
        return 1
    level = int(raw_level)
    get_level_config(level)  # validates level >= 1
    return level


class GameScene(Scene):
    """One game: owns the world for the current level and delegates per-tick flow to a GamePhase."""

    def __init__(self, manager, rng: random.Random | None = None):
        super().__init__(manager)
        self.rng = rng or random.Random()
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self.hud = Hud(self.font, self.sprites)
        self.session = GameSession(level=start_level_from_environment())
        self.felix = Felix()
        self.building: Building | None = None
        self.camera: Camera | None = None
        self.ralph: Ralph | None = None
        self.bricks: BrickField | None = None
        self.nicelanders: NicelanderDirector | None = None
        self.hazards: HazardField | None = None
        self.phase: GamePhase | None = None
        self.input_handler = self._null_input
        self._is_paused = False
        self._has_game_ended = False

    @property
    def palette(self) -> int:
        return (self.session.level - 1) % PALETTE_COUNT

    def on_enter(self):
        self.phase = self.start_level(self.session.level)

    def play_gameplay_music(self) -> None:
        """Start the in-level music; a no-op while it is already the current music.

        [EXE] Entering state 3 (FUN_00408fc0 case 3) calls FUN_0040f4a0(1) with
        ESI 0xe: sound 14, looping. Nothing plays it before that, so the climb-in
        and the ready pause keep whatever music was already going.
        """
        self.sound.play_music_index(GAMEPLAY_MUSIC, is_looping=True)

    def start_level(self, level: int) -> GamePhase:
        """Build a fresh world for the level and return its LevelStartPhase.

        Felix keeps his score and lives. The caller installs the returned phase.
        """
        self.session.level = level
        self.building = Building(level, self.rng)
        self.camera = Camera()
        self.ralph = Ralph(self.rng, self.session.drop_hazard_schedule)
        self.bricks = BrickField(self.rng)
        self.nicelanders = NicelanderDirector(self.rng)
        self.hazards = HazardField(self.rng)
        self.felix.place_at(RESPAWN_LOCAL_ROW, RESPAWN_COLUMN, self.building)
        return LevelStartPhase()

    def enter_play(self) -> GamePhase:
        """Hand off to play: Ralph leaves his idle pose and starts the patrol from the ledge."""
        self.ralph.place_on_ledge(self.building)
        self.hazards.start_section(self.building, get_level_config(self.session.level))
        self.play_gameplay_music()
        return PlayPhase()

    def end_game(self) -> None:
        """Hand off to the game-over screen. Safe to call more than once."""
        if self._has_game_ended:
            return
        self._has_game_ended = True
        # No sound here: the final hit already played sound 21 (FUN_0040ca00), and
        # the exe's game-over states 7 and 8 never touch the music.
        from scenes.game_over_scene import GameOverScene
        self.manager.replace(GameOverScene(self.manager, self.felix.score))

    def finish_game_end_screen(self) -> None:
        """After the "11022012" screen: the high-score flow, without the game-over screen.

        [USER] Score handling as after a game over: initials entry when the score
        qualifies, then the table, then the title. The exe skips initials entry
        here (FUN_0040a0f0 resets straight to attract) and resets the in-memory
        table (FUN_0040a060); scores.dat is never wiped (Ruling 28).
        """
        if self._has_game_ended:
            return
        self._has_game_ended = True
        from scenes.high_score_scene import HighScoreScene
        self.manager.replace(HighScoreScene(self.manager, self.felix.score))

    def tick(self, input_handler):
        """One game tick (1/60s). All game logic is tick-counted."""
        # Checked before the pause so a press is never lost (FUN_0040af70 latches it every tick).
        if input_handler.is_just_pressed(Action.END_GAME):
            self.session.is_end_game_requested = True
        self._update_pause(input_handler)
        if self._is_paused:
            return

        self.input_handler = input_handler
        self.camera.snapshot()
        next_phase = self.phase.tick(self)
        self.session.frame_counter += 1
        if next_phase is not None:
            self.phase = next_phase

    def _update_pause(self, input_handler):
        is_toggle_pressed = (input_handler.is_just_pressed(Action.START) or
                             input_handler.is_just_pressed(Action.PAUSE))
        if not self._is_paused and input_handler.has_lost_focus():
            self._set_paused(True)
        elif is_toggle_pressed:
            self._set_paused(not self._is_paused)

    @property
    def is_paused(self):
        """True while the game is paused (pause key or window focus loss)."""
        return self._is_paused

    def _set_paused(self, is_paused):
        self._is_paused = is_paused
        if is_paused:
            self.sound.pause_all()
        else:
            self.sound.resume_all()

    class _NullInput:
        def is_just_pressed(self, action):
            return False
        def is_pressed(self, action):
            return False

    _null_input = _NullInput()

    def draw(self, screen, alpha=1.0):
        # Interpolation blends each entity between its last two tick
        # positions; with ticks frozen, a cycling alpha would make moving
        # sprites shimmer in place. Hold them at their latest position.
        if self._is_paused:
            alpha = 1.0

        screen.fill(BLACK)
        self.phase.draw_world(self, screen, alpha)
        self.hud.draw(screen, self.felix.score, self.session.level, self.felix.lives, self.palette)
        self.phase.draw_overlay(self, screen)

        if self._is_paused:
            self._draw_pause_overlay(screen)

    def draw_play_world(self, screen, alpha):
        """Draw the building and every play entity, as the play phases show them."""
        self.building.draw_street(screen, self.sprites, self.camera, self.palette)
        # TODO: Building.draw takes no alpha, so during the section scroll the
        # building sits at the latest scroll while entities interpolate.
        self.building.draw(screen, self.sprites, self.camera, self.palette)
        # Nicelanders sit inside the windows, so they draw right after the building.
        self.nicelanders.draw(screen, self.sprites, self.building, self.camera, self.palette)
        self.bricks.draw(screen, self.sprites, self.camera, self.palette, alpha)
        self.hazards.draw(screen, self.sprites, self.building, self.camera, self.palette, alpha)
        self.ralph.draw(screen, self.sprites, self.camera, self.palette, alpha)
        self.felix.draw(screen, self.sprites, self.camera, self.palette, alpha)

    def _draw_pause_overlay(self, screen):
        dim = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))
        draw_centered_text(screen, self.font, "PAUSED", (GAME_WIDTH // 2, GAME_HEIGHT // 2 - 8),
                           preferred_scale=2.0)
        draw_centered_text(screen, self.font, "PRESS START",
                           (GAME_WIDTH // 2, GAME_HEIGHT // 2 + 16), color_row=1)
