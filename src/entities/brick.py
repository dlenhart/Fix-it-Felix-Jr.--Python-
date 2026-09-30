import pygame
from entities.building import GRID_COLS, WINDOW_WIDTH, WINDOW_HEIGHT


BRICK_FALL_SPEEDS = [-1.8, -2.2, -1.7, -1.5]  # Ghidra pass 3: types A-D
BRICK_DRIFT_SPEED = 1.7                        # _DAT_00416b9c


class Brick:
    def __init__(self, x, y, fall_speed, drift=0.0):
        self.x = float(x)
        self.y = float(y)
        self.fall_speed = fall_speed
        self.drift = drift
        self.width = 16
        self.height = 12
        self.active = True

    def tick(self):
        self.y -= self.fall_speed
        self.x += self.drift
        if self.y > 340:
            self.active = False
        return not self.active

    def check_window_collision(self, building):
        for row in range(building.current_rows):
            for col in range(GRID_COLS):
                wx, wy = building.get_window_pixel_pos(col, row)
                if (wx < self.x + self.width and
                    wx + WINDOW_WIDTH > self.x and
                    wy < self.y + self.height and
                    wy + WINDOW_HEIGHT > self.y):
                    return col, row
        return None

    def hits_felix(self, felix, building):
        fx, fy = felix.get_pixel_pos(building)
        return (fx < self.x + self.width and
                fx + WINDOW_WIDTH > self.x and
                fy < self.y + self.height and
                fy + WINDOW_HEIGHT > self.y)

    def draw(self, screen, sprite_sheet, palette):
        try:
            sprite = sprite_sheet.get_sprite("brick_falling", 0, palette)
            screen.blit(sprite, (int(self.x), int(self.y)))
        except (KeyError, IndexError):
            pygame.draw.rect(screen, (139, 90, 43),
                (int(self.x), int(self.y), self.width, self.height))
