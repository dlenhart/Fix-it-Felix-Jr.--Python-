import pygame
from entities.building import WINDOW_WIDTH, WINDOW_HEIGHT
from constants import GAME_WIDTH, SPRITE_FRAME_HOLD_TICKS


BIRD_SPEED_X = 2.2   # Ghidra pass 3: _DAT_00416b94


class Bird:
    def __init__(self, row, from_left, building):
        _, self.y = building.get_window_pixel_pos(0, row)
        self.y += WINDOW_HEIGHT // 3
        self.speed = BIRD_SPEED_X if from_left else -BIRD_SPEED_X
        self.x = float(-30 if from_left else GAME_WIDTH + 10)
        self._prev_x = self.x
        self.width = 24
        self.height = 16
        self.active = True
        self._anim_ticks = 0

    def tick(self):
        """Advance one tick."""
        self._prev_x = self.x
        self.x += self.speed
        self._anim_ticks += 1
        if self.x < -50 or self.x > GAME_WIDTH + 50:
            self.active = False
        return not self.active

    def hits_felix(self, felix, building):
        fx, fy = felix.get_pixel_pos(building)
        return (fx < self.x + self.width and
                fx + 24 > self.x and
                fy < self.y + self.height and
                fy + 36 > self.y)

    def draw(self, screen, sprite_sheet, palette, alpha=1.0):
        render_x = self._prev_x + (self.x - self._prev_x) * alpha
        sprite_name = "bird_right" if self.speed > 0 else "bird_left"
        frame = (self._anim_ticks // SPRITE_FRAME_HOLD_TICKS) % 2
        try:
            sprite = sprite_sheet.get_sprite(sprite_name, frame, palette)
            screen.blit(sprite, (int(render_x), int(self.y)))
        except (KeyError, IndexError):
            pygame.draw.polygon(screen, (80, 80, 80), [
                (int(render_x), int(self.y) + 8),
                (int(render_x) + 12, int(self.y)),
                (int(render_x) + 24, int(self.y) + 8),
                (int(render_x) + 12, int(self.y) + 16),
            ])
