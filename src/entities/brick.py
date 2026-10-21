import pygame
from entities.building import WINDOW_WIDTH, WINDOW_HEIGHT


BRICK_FALL_SPEEDS = [-1.8, -2.2, -1.7, -1.5]  # Ghidra pass 3: types A-D


class Brick:
    def __init__(self, x, y, fall_speed, drift=0.0):
        self.x = float(x)
        self.y = float(y)
        self._prev_x = self.x
        self._prev_y = self.y
        self.fall_speed = fall_speed
        self.drift = drift
        self.width = 16
        self.height = 12
        self.active = True

    def tick(self):
        self._prev_x = self.x
        self._prev_y = self.y
        self.y -= self.fall_speed
        self.x += self.drift
        if self.y > 340:
            self.active = False
        return not self.active

    def hits_felix(self, felix, building):
        fx, fy = felix.get_pixel_pos(building)
        return (fx < self.x + self.width and
                fx + WINDOW_WIDTH > self.x and
                fy < self.y + self.height and
                fy + WINDOW_HEIGHT > self.y)

    def draw(self, screen, sprite_sheet, palette, alpha=1.0):
        render_x = self._prev_x + (self.x - self._prev_x) * alpha
        render_y = self._prev_y + (self.y - self._prev_y) * alpha
        try:
            sprite = sprite_sheet.get_sprite("brick_falling", 0, palette)
            screen.blit(sprite, (int(render_x), int(render_y)))
        except (KeyError, IndexError):
            pygame.draw.rect(screen, (139, 90, 43),
                (int(render_x), int(render_y), self.width, self.height))
