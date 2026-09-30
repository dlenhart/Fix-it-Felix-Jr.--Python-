import pygame
from entities.building import WINDOW_WIDTH, WINDOW_HEIGHT
from constants import GAME_WIDTH


BIRD_SPEED_X = 2.2   # Ghidra pass 3: _DAT_00416b94


class Bird:
    def __init__(self, row, from_left, building):
        _, self.y = building.get_window_pixel_pos(0, row)
        self.y += WINDOW_HEIGHT // 3
        self.speed = BIRD_SPEED_X if from_left else -BIRD_SPEED_X
        self.x = float(-30 if from_left else GAME_WIDTH + 10)
        self.width = 24
        self.height = 16
        self.active = True
        self._anim_frame = 0
        self._anim_timer = 0.0

    def tick(self):
        """Advance one tick."""
        self.x += self.speed
        self._anim_frame = (self._anim_frame + 1) % 2
        if self.x < -50 or self.x > GAME_WIDTH + 50:
            self.active = False
        return not self.active

    def hits_felix(self, felix, building):
        fx, fy = felix.get_pixel_pos(building)
        return (fx < self.x + self.width and
                fx + 24 > self.x and
                fy < self.y + self.height and
                fy + 36 > self.y)

    def draw(self, screen, sprite_sheet, palette):
        sprite_name = "bird_right" if self.speed > 0 else "bird_left"
        try:
            sprite = sprite_sheet.get_sprite(sprite_name, self._anim_frame, palette)
            screen.blit(sprite, (int(self.x), int(self.y)))
        except (KeyError, IndexError):
            pygame.draw.polygon(screen, (80, 80, 80), [
                (int(self.x), int(self.y) + 8),
                (int(self.x) + 12, int(self.y)),
                (int(self.x) + 24, int(self.y) + 8),
                (int(self.x) + 12, int(self.y) + 16),
            ])
