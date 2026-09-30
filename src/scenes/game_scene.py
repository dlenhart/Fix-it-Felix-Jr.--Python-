import random
import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, SKY_BLUE
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer
from entities.felix import Felix, FelixState
from entities.ralph import Ralph
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
        self._bird_interval_ticks = 32
        self._bird_from_left = True
        self._pie_ticks = 0
        self._pie_interval_ticks = 120
        self._section_clear_ticks = 0
        self._is_section_clearing = False
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
        self._bird_interval_ticks = max(16, 32 - (self.level - bird_level_threshold) * 2)
        self._pie_interval_ticks = max(80, 120 - (self.level - 1) * 4)

    def tick(self, input_handler):
        """One game tick (250ms). All game logic is tick-counted."""
        if self._is_section_clearing:
            self._section_clear_ticks += 1
            if self._section_clear_ticks >= 8:  # 8 ticks = 2 real seconds
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
        self.bricks.extend(new_bricks)

        for brick in self.bricks[:]:
            brick.tick()
            if not brick.active:
                self.bricks.remove(brick)
                continue
            hit = brick.check_window_collision(self.building)
            if hit:
                col, row = hit
                self.building.damage_window(col, row)
                brick.active = False
                self.bricks.remove(brick)
                self.sound.play_sfx("window_break")
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
        self.level += 1
        self._start_level()
        self.sound.play_sfx("level_transition")

    def _game_over(self):
        self.sound.stop_music()
        self.sound.play_sfx("game_over")
        from scenes.game_over_scene import GameOverScene
        self.manager.replace(GameOverScene(self.manager, self.felix.score))

    def draw(self, screen):
        screen.fill(SKY_BLUE)
        self.building.draw(screen, self.sprites, self.palette)

        if self.pie:
            self.pie.draw(screen, self.sprites, self.palette)

        for brick in self.bricks:
            brick.draw(screen, self.sprites, self.palette)

        for bird in self.birds:
            bird.draw(screen, self.sprites, self.palette)

        self.ralph.draw(screen, self.sprites, self.palette)
        self.felix.draw(screen, self.sprites, self.palette, self.building)

        self._draw_hud(screen)

        if self._is_section_clearing:
            text = self.font.render_text("YOU FIXED IT!", color_row=0)
            scaled = pygame.transform.scale(text, (text.get_width() * 2, text.get_height() * 2))
            rect = scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2))
            screen.blit(scaled, rect)

    def _draw_hud(self, screen):
        # All in 240x320 space — no scaling needed, sprites are native size
        score_text = self.font.render_text(f"{self.felix.score:06d}", color_row=0)
        screen.blit(score_text, (GAME_WIDTH - score_text.get_width() - 4, 310))

        level_text = self.font.render_text(f"LEVEL {self.level}", color_row=0)
        screen.blit(level_text, (4, 4))

        lives_text = self.font.render_text(f"LIVES {self.felix.lives:02d}", color_row=0)
        screen.blit(lives_text, (4, 14))
