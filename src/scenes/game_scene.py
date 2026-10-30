import os
import random

import pygame

from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK
from input_handler import Action
from sprite_sheet import SpriteSheet
from sprite_data import LIFE_ICON_PIECE
from sound_manager import SoundManager
from font_renderer import FontRenderer, scale_text_to_fit
from camera import Camera
from entities.building import Building
from entities.felix import Felix, RESPAWN_COLUMN, RESPAWN_LOCAL_ROW
from entities.ralph import Ralph
from entities.brick import BrickField
from entities.hazards import HazardField
from entities.nicelander import NicelanderDirector
from level_config import get_level_config
from scenes.game_phases import GamePhase, LevelStartPhase

PALETTE_COUNT = 5
RALPH_START_X = 120  # Ruling 12: a fresh Ralph per level starts at the patrol center
HUD_BAND_HEIGHT = 24  # [ASSUMED] HUD layout (spec section 10)
HUD_SCORE_POSITION = (4, 4)  # [ASSUMED]
HUD_LEVEL_POSITION = (4, 14)  # [ASSUMED]
HUD_LIFE_ICONS_RIGHT_X = 236  # [ASSUMED]
HUD_LIFE_ICON_Y = 4  # [ASSUMED] centers the 16px icon in the band
HUD_LIFE_ICON_SPACING = 1  # [ASSUMED]
HUD_MAX_LIFE_ICONS = 5  # [ASSUMED]
HUD_LIFE_COUNT_GAP = 2  # [ASSUMED] gap between the xN text and the first icon
START_LEVEL_ENVIRONMENT_VARIABLE = "FELIX_START_LEVEL"


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
        self.level = start_level_from_environment()
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
        return (self.level - 1) % PALETTE_COUNT

    def on_enter(self):
        self.start_level(self.level)
        self.sound.play_music("gameplay_a")

    def start_level(self, level: int) -> None:
        """Build a fresh world for the level; Felix keeps his score and lives."""
        self.level = level
        self.building = Building(level, self.rng)
        self.camera = Camera()
        self.ralph = Ralph(self.rng)
        self.ralph.x = RALPH_START_X
        self.bricks = BrickField(self.rng)
        self.nicelanders = NicelanderDirector(self.rng)
        self.hazards = HazardField(self.rng)
        self.felix.place_at(RESPAWN_LOCAL_ROW, RESPAWN_COLUMN, self.building)
        self.phase = LevelStartPhase()

    def end_game(self) -> None:
        """Hand off to the game-over screen. Safe to call more than once."""
        if self._has_game_ended:
            return
        self._has_game_ended = True
        self.sound.stop_music()
        # TODO: GameOverScene.on_enter also plays "game_over", so it sounds twice.
        self.sound.play_sfx("game_over")
        from scenes.game_over_scene import GameOverScene
        self.manager.replace(GameOverScene(self.manager, self.felix.score))

    def tick(self, input_handler):
        """One game tick (1/60s). All game logic is tick-counted."""
        self._update_pause(input_handler)
        if self._is_paused:
            return

        self.input_handler = input_handler
        self.camera.snapshot()
        next_phase = self.phase.tick(self)
        if next_phase is not None:
            self.phase = next_phase

    def _update_pause(self, input_handler):
        is_toggle_pressed = (input_handler.is_just_pressed(Action.START) or
                             input_handler.is_just_pressed(Action.PAUSE))
        if not self._is_paused and input_handler.has_lost_focus():
            self._set_paused(True)
        elif is_toggle_pressed:
            self._set_paused(not self._is_paused)

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
        # TODO: Building.draw takes no alpha, so during the section scroll the
        # building sits at the latest scroll while entities interpolate.
        self.building.draw(screen, self.sprites, self.camera, self.palette)
        # Nicelanders sit inside the windows, so they draw right after the building.
        self.nicelanders.draw(screen, self.sprites, self.building, self.camera, self.palette)
        self.bricks.draw(screen, self.sprites, self.camera, self.palette, alpha)
        self.hazards.draw(screen, self.sprites, self.building, self.camera, self.palette, alpha)
        self.ralph.draw(screen, self.sprites, self.camera, self.palette, alpha)
        self.felix.draw(screen, self.sprites, self.camera, self.palette, alpha)

        self._draw_hud(screen)
        self.phase.draw_overlay(self, screen)

        if self._is_paused:
            self._draw_pause_overlay(screen)

    def _draw_pause_overlay(self, screen):
        dim = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        paused = self.font.render_text("PAUSED", color_row=0)
        scaled = scale_text_to_fit(paused, GAME_WIDTH - 16, preferred_scale=2.0)
        screen.blit(scaled, scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 - 8)))

        prompt = self.font.render_text("PRESS START", color_row=1)
        screen.blit(prompt, prompt.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 + 16)))

    def _draw_hud(self, screen):
        screen.fill(BLACK, pygame.Rect(0, 0, GAME_WIDTH, HUD_BAND_HEIGHT))

        score_text = self.font.render_text(f"{self.felix.score:06d}", color_row=0)
        screen.blit(score_text, HUD_SCORE_POSITION)

        level_text = self.font.render_text(f"LEVEL {self.level}", color_row=0)
        screen.blit(level_text, HUD_LEVEL_POSITION)

        self._draw_life_icons(screen)

    def _draw_life_icons(self, screen):
        icon = self.sprites.get_piece(LIFE_ICON_PIECE, self.palette)
        icon_count = min(self.felix.lives, HUD_MAX_LIFE_ICONS)
        left_x = HUD_LIFE_ICONS_RIGHT_X
        for _ in range(icon_count):
            left_x -= icon.get_width()
            screen.blit(icon, (left_x, HUD_LIFE_ICON_Y))
            left_x -= HUD_LIFE_ICON_SPACING

        if self.felix.lives <= HUD_MAX_LIFE_ICONS:
            return
        count_text = self.font.render_text(f"X{self.felix.lives}", color_row=0)
        text_y = HUD_LIFE_ICON_Y + (icon.get_height() - count_text.get_height()) // 2
        text_x = left_x - HUD_LIFE_COUNT_GAP - count_text.get_width()
        screen.blit(count_text, (text_x, text_y))
