import enum
import random
import pygame
from constants import GAME_WIDTH, GAME_HEIGHT


class WindowState(enum.Enum):
    INTACT = 0
    CRACKED = 1
    BROKEN = 2


WINDOW_SPRITE_MAP = {
    WindowState.INTACT: "window_intact",
    WindowState.CRACKED: "window_cracked",
    WindowState.BROKEN: "window_broken",
}

GRID_COLS = 5          # Confirmed by Ghidra: puVar3[0x13] = 5
SECTIONS_PER_LEVEL = 3

# Rows per section vary by type (Ghidra: (type != 2) + 6)
SECTION_TYPES = {
    0: {"rows": 7, "height": 12},
    1: {"rows": 7, "height": 13},
    2: {"rows": 6, "height": 10},
    3: {"rows": 7, "height": 11},
    4: {"rows": 7, "height": 9},   # Special: 5 sub-rows with explicit setup
}

# Coordinates in the 240x320 internal space
WINDOW_WIDTH = 24
WINDOW_HEIGHT = 24
GRID_LEFT = 20
GRID_TOP = 64          # Ghidra: DAT_004243d4 = 0x40 (64)
WINDOW_SPACING_X = 40
WINDOW_SPACING_Y = 36


class WindowSlot:
    def __init__(self):
        self.state = WindowState.INTACT

    def damage(self):
        if self.state == WindowState.INTACT:
            self.state = WindowState.CRACKED
        elif self.state == WindowState.CRACKED:
            self.state = WindowState.BROKEN

    def repair(self, is_super=False):
        if self.state == WindowState.INTACT:
            return False, False
        if is_super:
            self.state = WindowState.INTACT
            return True, True
        if self.state == WindowState.BROKEN:
            self.state = WindowState.CRACKED
            return True, False
        if self.state == WindowState.CRACKED:
            self.state = WindowState.INTACT
            return True, True
        return False, False


class Building:
    def __init__(self):
        self.current_section = 0
        self.sections = []
        self.section_types = []

    def _create_sections(self, type_list):
        self.sections = []
        self.section_types = type_list
        for section_type in type_list:
            rows = SECTION_TYPES[section_type]["rows"]
            section = [[WindowSlot() for _ in range(GRID_COLS)] for _ in range(rows)]
            self.sections.append(section)

    def reset_for_level(self, level):
        self.current_section = 0
        # Section type assignment varies by level
        # Levels 1-3: easier types (0, 1), Levels 4-7: mixed (2, 3), Level 8+: harder (3, 4)
        if level < 4:
            type_list = [0, 1, 0]
        elif level < 8:
            type_list = [2, 0, 3]
        else:
            type_list = [3, 2, 4]
        self._create_sections(type_list)
        initial_broken = min(3 + level, 12)
        for section in self.sections:
            num_rows = len(section)
            broken_count = min(initial_broken, GRID_COLS * num_rows)
            positions = [(r, c) for r in range(num_rows) for c in range(GRID_COLS)]
            random.shuffle(positions)
            for i in range(broken_count):
                r, c = positions[i]
                section[r][c].state = WindowState.BROKEN

    @property
    def _current_grid(self):
        return self.sections[self.current_section]

    def get_window_state(self, col, row):
        return self._current_grid[row][col].state

    def damage_window(self, col, row):
        if 0 <= col < GRID_COLS and 0 <= row < self.current_rows:
            self._current_grid[row][col].damage()

    def repair_window(self, col, row, is_super=False):
        if 0 <= col < GRID_COLS and 0 <= row < self.current_rows:
            return self._current_grid[row][col].repair(is_super)
        return False, False

    @property
    def current_rows(self):
        return len(self._current_grid)

    def is_section_clear(self):
        for row in self._current_grid:
            for window in row:
                if window.state != WindowState.INTACT:
                    return False
        return True

    def is_level_clear(self):
        return self.current_section >= len(self.sections)

    def advance_section(self):
        self.current_section += 1

    def get_window_pixel_pos(self, col, row):
        x = GRID_LEFT + col * WINDOW_SPACING_X
        y = GRID_TOP + (self.current_rows - 1 - row) * WINDOW_SPACING_Y
        return x, y

    def draw(self, screen, sprite_sheet, palette):
        # Draw brick wall background
        try:
            wall = sprite_sheet.get_sprite("wall_brick", 0, palette)
            for y in range(0, GAME_HEIGHT, wall.get_height()):
                for x in range(0, GAME_WIDTH, wall.get_width()):
                    screen.blit(wall, (x, y))
        except (KeyError, IndexError):
            screen.fill((139, 69, 19))

        # Draw windows
        for row in range(self.current_rows):
            for col in range(GRID_COLS):
                state = self.get_window_state(col, row)
                sprite_name = WINDOW_SPRITE_MAP[state]
                wx, wy = self.get_window_pixel_pos(col, row)
                try:
                    sprite = sprite_sheet.get_sprite(sprite_name, 0, palette)
                    screen.blit(sprite, (wx, wy))
                except (KeyError, IndexError):
                    color = {
                        WindowState.INTACT: (100, 149, 237),
                        WindowState.CRACKED: (200, 200, 100),
                        WindowState.BROKEN: (50, 50, 50),
                    }[state]
                    pygame.draw.rect(screen, color,
                        (wx, wy, WINDOW_WIDTH, WINDOW_HEIGHT))
                    pygame.draw.rect(screen, (200, 200, 200),
                        (wx, wy, WINDOW_WIDTH, WINDOW_HEIGHT), 2)
