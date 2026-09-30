import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK, SKY_BLUE
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer, scale_text_to_fit


# duration_ticks values are real-second durations from the design converted
# to tick counts at 4 ticks/sec: 2.0->8, 2.5->10, 2.5->10, 2.0->8, 2.0->8
CUTSCENE_STEPS = [
    {"duration_ticks": 8, "text": "", "sprite": "building_exterior"},
    {"duration_ticks": 10, "text": "HEY. YOU MOVED MY STUMP!", "sprite": "ralph_cutscene_idle"},
    {"duration_ticks": 10, "text": "I'M GONNA WRECK IT!", "sprite": "ralph_cutscene_smash"},
    {"duration_ticks": 8, "text": "FIX IT FELIX!", "sprite": None},
    {"duration_ticks": 8, "text": "I CAN FIX IT!", "sprite": None},
]


class CutsceneScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._step = 0
        self._ticks = 0

    def on_enter(self):
        self.sound.play_music("cutscene_intro", loop=False)

    def on_exit(self):
        self.sound.stop_music()

    def tick(self, input_handler):
        """One game tick (250ms). All game logic is tick-counted."""
        if (input_handler.is_just_pressed(Action.JUMP) or
                input_handler.is_just_pressed(Action.START)):
            self._start_game()
            return

        self._ticks += 1
        if self._step < len(CUTSCENE_STEPS):
            if self._ticks >= CUTSCENE_STEPS[self._step]["duration_ticks"]:
                self._ticks = 0
                self._step += 1
                if self._step >= len(CUTSCENE_STEPS):
                    self._start_game()

    def _start_game(self):
        from scenes.game_scene import GameScene
        self.manager.replace(GameScene(self.manager))

    def draw(self, screen, alpha=1.0):
        screen.fill(SKY_BLUE)

        if self._step >= len(CUTSCENE_STEPS):
            return

        step = CUTSCENE_STEPS[self._step]

        if step["sprite"]:
            try:
                sprite = self.sprites.get_sprite(step["sprite"], 0, 0)
                sprite_scaled = pygame.transform.scale(sprite,
                    (sprite.get_width() * 2, sprite.get_height() * 2))
                rect = sprite_scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 - 40))
                screen.blit(sprite_scaled, rect)
            except (KeyError, IndexError):
                pass

        if step["text"]:
            text = self.font.render_text(step["text"], color_row=0)
            scaled = scale_text_to_fit(text, GAME_WIDTH - 16, preferred_scale=2.0)
            rect = scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 + 80))
            screen.blit(scaled, rect)
