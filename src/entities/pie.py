import pygame
from entities.building import WINDOW_WIDTH, WINDOW_HEIGHT


PIE_LINGER_TICKS = 20  # ~5 real seconds at 4 Hz


class Pie:
    def __init__(self, col, row, building):
        self.col = col
        self.row = row
        wx, wy = building.get_window_pixel_pos(col, row)
        self.x = wx + WINDOW_WIDTH // 2 - 8
        self.y = wy - 12
        self.width = 16
        self.height = 12
        self.active = True
        self._timer = 0.0
        self._ticks = 0
        self._blink = False

    def tick(self):
        self._ticks += 1
        if self._ticks >= PIE_LINGER_TICKS - 6:  # Blink in last ~1.5 seconds
            self._blink = not self._blink
        if self._ticks >= PIE_LINGER_TICKS:
            self.active = False
        return not self.active

    def collected_by_felix(self, felix, building):
        return (self.active and
                felix.col == self.col and
                felix.row == self.row)

    def draw(self, screen, sprite_sheet, palette):
        if not self.active or self._blink:
            return
        try:
            sprite = sprite_sheet.get_sprite("pie", 0, palette)
            screen.blit(sprite, (int(self.x), int(self.y)))
        except (KeyError, IndexError):
            pygame.draw.ellipse(screen, (255, 220, 150),
                (int(self.x), int(self.y), self.width, self.height))
