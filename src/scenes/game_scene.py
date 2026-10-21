import random
import pygame
from scene_manager import Scene
from constants import (
    GAME_WIDTH, GAME_HEIGHT, SKY_BLUE, SECTION_CLEAR_TICKS,
    BIRD_BASE_INTERVAL_TICKS, BIRD_INTERVAL_STEP_TICKS, BIRD_MIN_INTERVAL_TICKS,
    PIE_SPAWN_INTERVAL_TICKS, PIE_SPAWN_INTERVAL_STEP_TICKS, PIE_SPAWN_MIN_INTERVAL_TICKS,
)
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer, scale_text_to_fit
from entities.felix import Felix, FelixState
from entities.ralph import Ralph, MAX_BRICKS
from entities.building import Building, GRID_COLS
from entities.brick import Brick
from entities.bird import Bird
from entities.pie import Pie


class GameScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self.building = Building()
        self.felix = Felix()
        self.ralph = Ralph()
        self.bricks = []
        self.birds = []
        self.pie = None
        self.level = 1
        self.palette = 0
        self._bird_ticks = 0
        self._bird_interval_ticks = BIRD_BASE_INTERVAL_TICKS
        self._bird_from_left = True
        self._pie_ticks = 0
        self._pie_interval_ticks = PIE_SPAWN_INTERVAL_TICKS
        self._section_clear_ticks = 0
        self._is_section_clearing = False
        self._is_paused = False
        self._high_score = 0

    def on_enter(self):
        self._start_level()
        self.sound.play_music("gameplay_a")

    def _start_level(self):
        self.building.reset_for_level(self.level)
        self.felix.reset_position()
        self.ralph.configure_for_level(self.level)
        self.palette = (self.level - 1) % 5
        self.bricks.clear()
        self.birds.clear()
        self.pie = None
        self._bird_ticks = 0
        self._pie_ticks = 0
        self._is_section_clearing = False

        bird_level_threshold = 2
        self._bird_interval_ticks = max(
            BIRD_MIN_INTERVAL_TICKS,
            BIRD_BASE_INTERVAL_TICKS - (self.level - bird_level_threshold) * BIRD_INTERVAL_STEP_TICKS)
        self._pie_interval_ticks = max(
            PIE_SPAWN_MIN_INTERVAL_TICKS,
            PIE_SPAWN_INTERVAL_TICKS - (self.level - 1) * PIE_SPAWN_INTERVAL_STEP_TICKS)

    def tick(self, input_handler):
        """One game tick (1/60s). All game logic is tick-counted."""
        self._update_pause(input_handler)
        if self._is_paused:
            return

        if self._is_section_clearing:
            self._section_clear_ticks += 1
            if self._section_clear_ticks >= SECTION_CLEAR_TICKS:
                self._is_section_clearing = False
                if self.building.is_level_clear():
                    self._advance_level()
                else:
                    self.felix.reset_position()
                    self.bricks.clear()
                    self.birds.clear()
                    self.pie = None
            return

        self.felix.tick(input_handler, self.building, self.sound)

        new_bricks = self.ralph.tick(self.felix, self.building, self.sound)
        available_slots = MAX_BRICKS - len(self.bricks)
        if available_slots > 0:
            self.bricks.extend(new_bricks[:available_slots])

        for brick in self.bricks[:]:
            brick.tick()
            if not brick.active:
                self.bricks.remove(brick)
                continue
            if brick.hits_felix(self.felix, self.building):
                self.felix.stun(self.sound)
                brick.active = False
                self.bricks.remove(brick)
                if not self.felix.is_alive:
                    self._game_over()
                    return

        if self.level >= 2:
            self._bird_ticks += 1
            if self._bird_ticks >= self._bird_interval_ticks:
                self._bird_ticks = 0
                bird_row = random.randint(0, self.building.current_rows - 1)
                bird = Bird(bird_row, self._bird_from_left, self.building)
                self.birds.append(bird)
                self._bird_from_left = not self._bird_from_left

        for bird in self.birds[:]:
            bird.tick()
            if not bird.active:
                self.birds.remove(bird)
                continue
            if bird.hits_felix(self.felix, self.building):
                self.felix.stun(self.sound)
                bird.active = False
                self.birds.remove(bird)
                if not self.felix.is_alive:
                    self._game_over()
                    return

        self._pie_ticks += 1
        if self._pie_ticks >= self._pie_interval_ticks and self.pie is None:
            self._pie_ticks = 0
            pie_col = random.randint(0, GRID_COLS - 1)
            pie_row = random.randint(0, self.building.current_rows - 1)
            self.pie = Pie(pie_col, pie_row, self.building)
            self.sound.play_sfx("pie_throw")

        if self.pie:
            self.pie.tick()
            if not self.pie.active:
                self.pie = None
            elif self.pie.collected_by_felix(self.felix, self.building):
                self.felix.activate_super(self.sound)
                self.sound.play_sfx("pie_pickup")
                self.pie = None

        if self.building.is_section_clear():
            self._section_clear()

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

    def _section_clear(self):
        self._is_section_clearing = True
        self._section_clear_ticks = 0
        self.felix.state = FelixState.CELEBRATING
        self.building.advance_section()
        self.sound.play_sfx("section_clear")
        self.bricks.clear()
        self.birds.clear()

    def _advance_level(self):
        self.sound.stop_music()
        from scenes.level_clear_scene import LevelClearScene
        self.manager.replace(LevelClearScene(
            self.manager, self.level, self.felix.score))

    def _game_over(self):
        self.sound.stop_music()
        self.sound.play_sfx("game_over")
        from scenes.game_over_scene import GameOverScene
        self.manager.replace(GameOverScene(self.manager, self.felix.score))

    def draw(self, screen, alpha=1.0):
        # Interpolation blends each entity between its last two tick
        # positions; with ticks frozen, a cycling alpha would make moving
        # sprites shimmer in place. Hold them at their latest position.
        if self._is_paused:
            alpha = 1.0

        screen.fill(SKY_BLUE)
        self.building.draw(screen, self.sprites, self.palette)

        if self.pie:
            self.pie.draw(screen, self.sprites, self.palette)

        for brick in self.bricks:
            brick.draw(screen, self.sprites, self.palette, alpha)

        for bird in self.birds:
            bird.draw(screen, self.sprites, self.palette, alpha)

        self.ralph.draw(screen, self.sprites, self.palette)
        self.felix.draw(screen, self.sprites, self.palette, self.building, alpha)

        self._draw_hud(screen)

        if self._is_section_clearing:
            text = self.font.render_text("YOU FIXED IT!", color_row=0)
            scaled = scale_text_to_fit(text, GAME_WIDTH - 16, preferred_scale=2.0)
            rect = scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2))
            screen.blit(scaled, rect)

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
        # All in 240x320 space — no scaling needed, sprites are native size.
        # Score sits top-right, opposite LEVEL/LIVES, over open brick above
        # the building — at the bottom it overlapped the lowest window row.
        score_text = self.font.render_text(f"{self.felix.score:06d}", color_row=0)
        screen.blit(score_text, (GAME_WIDTH - score_text.get_width() - 4, 4))

        level_text = self.font.render_text(f"LEVEL {self.level}", color_row=0)
        screen.blit(level_text, (4, 4))

        lives_text = self.font.render_text(f"LIVES {self.felix.lives:02d}", color_row=0)
        screen.blit(lives_text, (4, 14))
