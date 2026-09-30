# Fix-It Felix Jr. Pygame Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Fix-It Felix Jr. as a faithful Pygame recreation using the original sprite sheets, sounds, and assets from the Windows executable.

**Architecture:** Scene-based state machine. SceneManager drives a stack of scenes (Title, Cutscene, Game, LevelClear, GameOver, HighScore). Entities (Felix, Ralph, Brick, Bird, Pie) are plain classes managed by GameScene. Sprites are manually extracted from 1024x1024 atlas PNGs via bounding-box definitions. All input abstracted through a unified handler supporting keyboard and gamepad.

**Tech Stack:** Python 3.10+, Pygame 2.1+, Pillow (dev tool only — for sprite extraction helper)

## Global Constraints

- Python 3 + Pygame only — no other runtime dependencies
- **240×320 internal resolution** (portrait, confirmed by Ghidra), scaled up to display window (3× = 720×960)
- **250ms fixed-step game logic** (confirmed by Ghidra: `SetTimer(0xFA)`), render at 60 FPS with tick accumulator
- Single player only
- All assets live in `Data/` (untouched) and project root (boot loader BMPs)
- No TDD — write implementation first, tests after for logic-layer code
- GUI/rendering code verified manually — never launch browser automation
- Keyboard + gamepad input via unified abstraction
- Spec: `docs/superpowers/specs/2026-06-17-fix-it-felix-pygame-design.md`
- Ghidra findings: `docs/superpowers/specs/2026-06-17-ghidra-analysis-findings.md`

## Key Constants (Ghidra-Verified)

| Constant | Value | Notes |
|----------|-------|-------|
| Internal resolution | 240×320 | Portrait orientation |
| Tick rate | 250ms (4 Hz) | All game timing in ticks |
| Initial lives | 10 | `_DAT_00424258 = 10` |
| Windows per row | 5 | `puVar3[0x13] = 5` |
| Rows per section | 6-7 | `(type != 2) + 6` |
| Section types | 5 (0-4) | Different window layouts |
| Felix states | 11 | States 0-10 |
| Max bricks | 4 pairs | Loop count = 4 |
| Window entities/player | 32 | `0x20` |
| HS entries | 5 | Loop bound |
| HS initials | 3 chars | "AAA" default |
| HS charset | 38 chars | " A-Z 0-9 ." |
| HS entry timer | 1800 ticks | Displayed as 30 (÷60) |
| Score format | %06d | 6-digit zero-padded |

### Movement & Physics Constants (Pass 3)

Movement uses **float-based velocity/acceleration**, NOT grid snapping. All speeds are in pixels per tick (250ms) in 240×320 internal space.

| Constant | Value | Source |
|----------|-------|--------|
| Max horizontal speed | ±2.0 px/tick | `_DAT_00416b40/44` |
| Initial vertical velocity | ±0.2 px/tick | `_DAT_00416b88/8c` |
| Jump initial X velocity | -5.0 px/tick | `_DAT_00416c00` |
| Jump arc divisor | 10.0 | `_DAT_00416c04` |
| Fall terminal velocity | 8.0 px/tick | `_DAT_00416b58` |
| Hammer start Y offset | -7.0 | `_DAT_00416b68` |
| Walk start X offset | -6.0 | `_DAT_00416b08` |
| Stun knockback Y | 480 (above screen) | `0x1e0` in FUN_0040bc80 |
| Brick fall velocity (type A) | -1.8 px/tick | `_DAT_00416b98` |
| Brick fall velocity (type B) | -2.2 px/tick | `_DAT_00416ba4` |
| Brick fall velocity (type C) | -1.7 px/tick | `_DAT_00416ba8` |
| Brick drift X velocity | 1.7 px/tick | `_DAT_00416b9c` |
| Bird X velocity | 2.2 px/tick | `_DAT_00416b94` |
| Bird Y velocity | -4.0 px/tick | `_DAT_00416b90` |
| Y coord: screen bottom area | 317.0 | `DAT_00416bac` |
| Y coord: lower play area | 304.0 | `DAT_00416bbc` |
| Y coord: mid screen | 170.0 | `DAT_00416bd0` |

### Estimated Constants (calibrate during playtesting)

These were runtime-initialized (zero in binary), so we estimate reasonable values:

| Constant | Estimate | Reasoning |
|----------|----------|-----------|
| Horizontal acceleration | 0.5 px/tick² | Reaches max speed (2.0) in ~4 ticks (1 sec) |
| Vertical move rate (walk) | 4.0 px/tick | Cross one row (~36px) in ~9 ticks (~2.25 sec) |
| Per-tick delta | 1.0 | Normalized multiplier |
| Hammer animation rate | 1.0 px/tick | Completes swing in ~7 ticks (~1.75 sec) |
| Gravity acceleration | 0.5 px/tick² | Reaches terminal vel (8.0) in ~16 ticks |
| Bonus life threshold | 10000 pts | Standard arcade convention |
| Super Felix duration | 40 ticks (10 sec) | Reasonable power-up window |
| Pie spawn interval | 120 ticks (30 sec) | Rare reward |
| Brick throw interval (base) | 12 ticks (3 sec) | Decreases with level |

---

### Task 1: Project Scaffold, Constants, and Main Loop

**Files:**
- Create: `src/constants.py`
- Create: `src/scene_manager.py`
- Create: `src/main.py`

**Interfaces:**
- Produces: `SceneManager` class with `push(scene)`, `replace(scene)`, `pop()`, `tick(input_handler)`, `draw(screen)` methods
- Produces: `Scene` base class with `tick(input_handler)`, `draw(screen)` methods
- Produces: Constants for internal resolution (240×320), display scale, tick rate, colors

- [ ] **Step 1: Create `src/constants.py`**

```python
import os

# Internal game resolution (confirmed by Ghidra: 240x320 portrait)
GAME_WIDTH = 240
GAME_HEIGHT = 320

# Display scaling
DISPLAY_SCALE = 3
DISPLAY_WIDTH = GAME_WIDTH * DISPLAY_SCALE   # 720
DISPLAY_HEIGHT = GAME_HEIGHT * DISPLAY_SCALE  # 960

# Timing (confirmed by Ghidra: SetTimer with 250ms)
TICK_RATE = 0.25       # 250ms per game tick
TICKS_PER_SECOND = 4   # Game logic advances 4 times per second
RENDER_FPS = 60        # Display refresh rate

# Ghidra-confirmed constants
INITIAL_LIVES = 10
GRID_COLS = 5
HIGH_SCORE_ENTRIES = 5
HIGH_SCORE_INITIALS = 3
HIGH_SCORE_CHARSET = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."
HS_ENTRY_TIMER_TICKS = 1800   # 30 displayed seconds (÷60)
HS_DISPLAY_TIMER_TICKS = 900
TIME_DISPLAY_DIVISOR = 60     # Ticks per displayed "second"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(PROJECT_ROOT, "Data")
BOOT_DIR = PROJECT_ROOT

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
SKY_BLUE = (92, 148, 252)

# Movement & Physics (Ghidra pass 3 — all in px/tick in 240x320 space)
FELIX_MAX_HORIZONTAL_SPEED = 2.0       # _DAT_00416b40
FELIX_INITIAL_VERTICAL_VEL = 0.2       # _DAT_00416b88
FELIX_JUMP_INITIAL_X_VEL = -5.0        # _DAT_00416c00
FELIX_JUMP_ARC_DIVISOR = 10.0          # _DAT_00416c04
FELIX_FALL_TERMINAL_VEL = 8.0          # _DAT_00416b58
FELIX_HAMMER_START_OFFSET = -7.0       # _DAT_00416b68
FELIX_WALK_START_X_OFFSET = -6.0       # _DAT_00416b08
FELIX_STUN_KNOCKBACK_Y = 480.0         # 0x1e0

# Estimated (runtime-initialized zeros in binary — calibrate during playtesting)
FELIX_HORIZONTAL_ACCEL = 0.5
FELIX_VERTICAL_MOVE_RATE = 4.0
FELIX_GRAVITY_ACCEL = 0.5
HAMMER_ANIM_RATE = 1.0
BONUS_LIFE_THRESHOLD = 10000
SUPER_DURATION_TICKS = 40
PIE_SPAWN_INTERVAL_TICKS = 120
BRICK_THROW_BASE_INTERVAL_TICKS = 12

# Entity velocities (Ghidra pass 3)
BRICK_FALL_VEL_A = -1.8               # _DAT_00416b98
BRICK_FALL_VEL_B = -2.2               # _DAT_00416ba4
BRICK_FALL_VEL_C = -1.7               # _DAT_00416ba8
BRICK_DRIFT_X_VEL = 1.7               # _DAT_00416b9c
BIRD_X_VEL = 2.2                      # _DAT_00416b94
BIRD_Y_VEL = -4.0                     # _DAT_00416b90
```

- [ ] **Step 2: Create `src/scene_manager.py`**

```python
class Scene:
    def __init__(self, manager):
        self.manager = manager

    def tick(self, input_handler):
        """Called once per game tick (every 250ms). All game logic goes here."""
        pass

    def draw(self, screen):
        """Called every render frame (60fps). Only drawing, no logic."""
        pass

    def on_enter(self):
        pass

    def on_exit(self):
        pass


class SceneManager:
    def __init__(self):
        self._stack = []

    @property
    def current(self):
        return self._stack[-1] if self._stack else None

    def push(self, scene):
        if self.current:
            self.current.on_exit()
        self._stack.append(scene)
        scene.on_enter()

    def replace(self, scene):
        if self.current:
            self.current.on_exit()
            self._stack.pop()
        self._stack.append(scene)
        scene.on_enter()

    def pop(self):
        if self.current:
            self.current.on_exit()
            self._stack.pop()
        if self.current:
            self.current.on_enter()

    def tick(self, input_handler):
        if self.current:
            self.current.tick(input_handler)

    def draw(self, screen):
        if self.current:
            self.current.draw(screen)
```

- [ ] **Step 3: Create `src/main.py` with a placeholder test scene**

```python
import pygame
from constants import (GAME_WIDTH, GAME_HEIGHT, DISPLAY_WIDTH, DISPLAY_HEIGHT,
                       RENDER_FPS, TICK_RATE, BLACK, WHITE)
from scene_manager import SceneManager, Scene


class PlaceholderScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.font = pygame.font.SysFont("monospace", 8)

    def draw(self, screen):
        screen.fill(BLACK)
        text = self.font.render("FIX-IT FELIX JR", True, WHITE)
        rect = text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2))
        screen.blit(text, rect)


def main():
    pygame.init()
    display = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT))
    pygame.display.set_caption("Fix-It Felix Jr.")
    clock = pygame.time.Clock()

    # Internal 240x320 surface — all game rendering happens here
    game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))

    scene_manager = SceneManager()
    scene_manager.push(PlaceholderScene(scene_manager))

    tick_accumulator = 0.0
    running = True
    while running:
        dt = clock.tick(RENDER_FPS) / 1000.0
        tick_accumulator += dt

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # Fixed-step game logic at 250ms per tick (4 Hz)
        while tick_accumulator >= TICK_RATE:
            scene_manager.tick(None)
            tick_accumulator -= TICK_RATE

        # Render at 60fps to internal surface, then scale up
        scene_manager.draw(game_surface)
        scaled = pygame.transform.scale(game_surface, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        display.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify the scaffold works**

Run: `cd src && python3 main.py`
Expected: A 720×960 window opens (portrait orientation) showing "FIX-IT FELIX JR" text scaled up on a black background. Close with Escape or window close.

- [ ] **Step 5: Commit**

```bash
git add src/constants.py src/scene_manager.py src/main.py
git commit -m "feat: project scaffold with constants, scene manager, and main loop"
```

---

### Task 2: Input Handler

**Files:**
- Create: `src/input_handler.py`

**Interfaces:**
- Produces: `Action` enum with `UP, DOWN, LEFT, RIGHT, JUMP, START, QUIT`
- Produces: `InputHandler` class with `poll(events)`, `is_pressed(action) -> bool`, `is_just_pressed(action) -> bool`

- [ ] **Step 1: Create `src/input_handler.py`**

```python
import enum
import pygame


class Action(enum.Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    JUMP = "jump"
    START = "start"
    QUIT = "quit"


KEYBOARD_MAP = {
    pygame.K_UP: Action.UP,
    pygame.K_DOWN: Action.DOWN,
    pygame.K_LEFT: Action.LEFT,
    pygame.K_RIGHT: Action.RIGHT,
    pygame.K_SPACE: Action.JUMP,
    pygame.K_z: Action.JUMP,
    pygame.K_RETURN: Action.START,
    pygame.K_ESCAPE: Action.QUIT,
}

GAMEPAD_BUTTON_MAP = {
    0: Action.JUMP,
    7: Action.START,
    6: Action.QUIT,
}

HAT_MAP = {
    (0, 1): Action.UP,
    (0, -1): Action.DOWN,
    (-1, 0): Action.LEFT,
    (1, 0): Action.RIGHT,
}

AXIS_THRESHOLD = 0.5


class InputHandler:
    def __init__(self):
        self._pressed = set()
        self._just_pressed = set()
        self._joystick = None
        self._init_joystick()

    def _init_joystick(self):
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

    def poll(self, events):
        self._just_pressed.clear()
        prev_pressed = self._pressed.copy()
        self._pressed.clear()

        for event in events:
            if event.type == pygame.JOYDEVICEADDED:
                self._init_joystick()
            elif event.type == pygame.JOYDEVICEREMOVED:
                self._joystick = None

        keys = pygame.key.get_pressed()
        for key, action in KEYBOARD_MAP.items():
            if keys[key]:
                self._pressed.add(action)

        if self._joystick:
            for btn, action in GAMEPAD_BUTTON_MAP.items():
                if btn < self._joystick.get_numbuttons() and self._joystick.get_button(btn):
                    self._pressed.add(action)

            if self._joystick.get_numhats() > 0:
                hat = self._joystick.get_hat(0)
                if hat in HAT_MAP:
                    self._pressed.add(HAT_MAP[hat])

            if self._joystick.get_numaxes() >= 2:
                x_axis = self._joystick.get_axis(0)
                y_axis = self._joystick.get_axis(1)
                if x_axis < -AXIS_THRESHOLD:
                    self._pressed.add(Action.LEFT)
                elif x_axis > AXIS_THRESHOLD:
                    self._pressed.add(Action.RIGHT)
                if y_axis < -AXIS_THRESHOLD:
                    self._pressed.add(Action.UP)
                elif y_axis > AXIS_THRESHOLD:
                    self._pressed.add(Action.DOWN)

        self._just_pressed = self._pressed - prev_pressed

    def is_pressed(self, action):
        return action in self._pressed

    def is_just_pressed(self, action):
        return action in self._just_pressed
```

- [ ] **Step 2: Integrate into `main.py`**

Update the main loop in `src/main.py` to use `InputHandler`:

```python
from input_handler import InputHandler, Action
```

Replace the event loop section:

```python
    input_handler = InputHandler()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        input_handler.poll(events)
        if input_handler.is_just_pressed(Action.QUIT):
            running = False

        scene_manager.handle_input(input_handler)
        scene_manager.update(dt)
        scene_manager.draw(screen)
        pygame.display.flip()
```

- [ ] **Step 3: Verify input works**

Run: `cd src && python3 main.py`
Expected: Window opens. Escape closes it. No errors.

- [ ] **Step 4: Commit**

```bash
git add src/input_handler.py src/main.py
git commit -m "feat: unified input handler with keyboard and gamepad support"
```

---

### Task 3: Sprite Sheet Loader, Extraction Tool, and Sprite Data

This is the biggest foundational task. It creates the sprite system and a visual extraction tool to precisely map all sprite bounding boxes.

**Files:**
- Create: `src/sprite_sheet.py`
- Create: `src/sprite_data.py`
- Create: `tools/sprite_viewer.py` (dev-only visual tool)

**Interfaces:**
- Produces: `SpriteSheet` class with `get_sprite(name, frame=0, palette=0) -> pygame.Surface`
- Produces: `SPRITES` dict in `sprite_data.py` mapping names to lists of `(x, y, w, h)` tuples

- [ ] **Step 1: Create `src/sprite_sheet.py`**

```python
import os
import pygame
from constants import ASSET_DIR


class SpriteSheet:
    def __init__(self):
        self._atlases = {}
        self._cache = {}

    def _get_atlas(self, palette):
        if palette not in self._atlases:
            path = os.path.join(ASSET_DIR, f"felix{palette}.png")
            surface = pygame.image.load(path).convert_alpha()
            self._atlases[palette] = surface
        return self._atlases[palette]

    def get_sprite(self, name, frame=0, palette=0):
        cache_key = (name, frame, palette)
        if cache_key in self._cache:
            return self._cache[cache_key]

        from sprite_data import SPRITES
        frames = SPRITES.get(name)
        if not frames:
            raise KeyError(f"Unknown sprite: {name}")
        if frame >= len(frames):
            raise IndexError(f"Sprite '{name}' has {len(frames)} frames, requested {frame}")

        x, y, w, h = frames[frame]
        atlas = self._get_atlas(palette)
        surface = atlas.subsurface(pygame.Rect(x, y, w, h)).copy()
        self._cache[cache_key] = surface
        return surface

    def get_frame_count(self, name):
        from sprite_data import SPRITES
        frames = SPRITES.get(name)
        return len(frames) if frames else 0


class HammerSheet:
    def __init__(self):
        self._atlases = {}
        self._cache = {}

    def _get_atlas(self, variant):
        if variant not in self._atlases:
            path = os.path.join(ASSET_DIR, f"hammer{variant}.png")
            surface = pygame.image.load(path).convert_alpha()
            self._atlases[variant] = surface
        return self._atlases[variant]

    def get_sprite(self, name, frame=0, variant=0):
        cache_key = (name, frame, variant)
        if cache_key in self._cache:
            return self._cache[cache_key]

        from sprite_data import HAMMER_SPRITES
        frames = HAMMER_SPRITES.get(name)
        if not frames:
            raise KeyError(f"Unknown hammer sprite: {name}")

        x, y, w, h = frames[frame]
        atlas = self._get_atlas(variant)
        surface = atlas.subsurface(pygame.Rect(x, y, w, h)).copy()
        self._cache[cache_key] = surface
        return surface
```

- [ ] **Step 2: Create `tools/sprite_viewer.py`** — interactive tool for mapping sprite coordinates

This tool displays the atlas and lets you click to identify sprite regions. It shows coordinates and dimensions as you drag rectangles over sprites.

```python
"""Interactive sprite atlas viewer for identifying bounding boxes.

Usage: python3 tools/sprite_viewer.py [palette_number]

Controls:
  - Click and drag to select a region
  - Mouse wheel to zoom in/out
  - Arrow keys to pan
  - P + number to switch palette (0-4)
  - H to switch to hammer sheets
  - Escape to quit

Prints (x, y, w, h) of selected region to stdout.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame
from constants import ASSET_DIR

pygame.init()

VIEWER_WIDTH = 1200
VIEWER_HEIGHT = 900

screen = pygame.display.set_mode((VIEWER_WIDTH, VIEWER_HEIGHT))
pygame.display.set_caption("Sprite Atlas Viewer")
clock = pygame.time.Clock()
font = pygame.font.SysFont("monospace", 14)

palette = int(sys.argv[1]) if len(sys.argv) > 1 else 0
showing_hammer = False


def load_atlas():
    if showing_hammer:
        path = os.path.join(ASSET_DIR, f"hammer{palette}.png")
    else:
        path = os.path.join(ASSET_DIR, f"felix{palette}.png")
    return pygame.image.load(path).convert_alpha()


atlas = load_atlas()
zoom = 1.0
pan_x, pan_y = 0, 0
drag_start = None
drag_end = None
selected_rect = None

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_h:
                showing_hammer = not showing_hammer
                atlas = load_atlas()
            elif event.key in (pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                palette = event.key - pygame.K_0
                atlas = load_atlas()
            elif event.key == pygame.K_LEFT:
                pan_x += 50
            elif event.key == pygame.K_RIGHT:
                pan_x -= 50
            elif event.key == pygame.K_UP:
                pan_y += 50
            elif event.key == pygame.K_DOWN:
                pan_y -= 50
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                drag_start = event.pos
                drag_end = event.pos
            elif event.button == 4:
                zoom = min(zoom * 1.2, 8.0)
            elif event.button == 5:
                zoom = max(zoom / 1.2, 0.25)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and drag_start:
                drag_end = event.pos
                sx = int((min(drag_start[0], drag_end[0]) - pan_x) / zoom)
                sy = int((min(drag_start[1], drag_end[1]) - pan_y) / zoom)
                ex = int((max(drag_start[0], drag_end[0]) - pan_x) / zoom)
                ey = int((max(drag_start[1], drag_end[1]) - pan_y) / zoom)
                w = ex - sx
                h = ey - sy
                if w > 2 and h > 2:
                    selected_rect = (sx, sy, w, h)
                    print(f"({sx}, {sy}, {w}, {h}),")
                drag_start = None
        elif event.type == pygame.MOUSEMOTION:
            if drag_start:
                drag_end = event.pos

    screen.fill((40, 40, 40))

    scaled = pygame.transform.scale(atlas, (int(1024 * zoom), int(1024 * zoom)))
    screen.blit(scaled, (pan_x, pan_y))

    if drag_start and drag_end:
        rect = pygame.Rect(
            min(drag_start[0], drag_end[0]),
            min(drag_start[1], drag_end[1]),
            abs(drag_end[0] - drag_start[0]),
            abs(drag_end[1] - drag_start[1]),
        )
        pygame.draw.rect(screen, (255, 255, 0), rect, 2)
        sx = int((rect.x - pan_x) / zoom)
        sy = int((rect.y - pan_y) / zoom)
        sw = int(rect.w / zoom)
        sh = int(rect.h / zoom)
        info = font.render(f"({sx}, {sy}, {sw}, {sh})", True, (255, 255, 0))
        screen.blit(info, (rect.x, rect.y - 18))

    if selected_rect:
        sx, sy, sw, sh = selected_rect
        draw_rect = pygame.Rect(
            int(sx * zoom + pan_x), int(sy * zoom + pan_y),
            int(sw * zoom), int(sh * zoom)
        )
        pygame.draw.rect(screen, (0, 255, 0), draw_rect, 2)

    mx, my = pygame.mouse.get_pos()
    atlas_x = int((mx - pan_x) / zoom)
    atlas_y = int((my - pan_y) / zoom)
    coords = font.render(f"Atlas: ({atlas_x}, {atlas_y})  Zoom: {zoom:.1f}x  Palette: {palette}  {'HAMMER' if showing_hammer else 'FELIX'}", True, (255, 255, 255))
    screen.blit(coords, (10, VIEWER_HEIGHT - 24))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
```

- [ ] **Step 3: Use the sprite viewer to map sprite coordinates and create `src/sprite_data.py`**

Run: `python3 tools/sprite_viewer.py`

Use the viewer to click and drag rectangles over each sprite in the atlas. The tool prints `(x, y, w, h)` tuples to stdout. Zoom in with mouse wheel for precision. Map all sprites below.

The atlas layout (from density analysis of felix0.png) has these major regions:
- **Building facade**: top-left (x=0-208, y=0-224) — brick walls, windows, ledges
- **Windows/signs**: top-center (x=208-480, y=0-160) — Niceland signs, window types, title logo, copyright
- **Medals/ribbons**: top-right (x=500-830, y=0-120)
- **Construction vehicles**: right side (x=500-830, y=48-180) — not needed for gameplay
- **Felix sprites**: rows of small figures (x=0-500, y=160-310) — each ~25-35px wide, ~35-45px tall
- **Ralph sprites**: large figures (x=0-450, y=310-610) — each ~60-100px wide, ~80-120px tall
- **Text overlays**: right side (x=520-830, y=460-520)
- **Trees/clouds**: (x=420-560, y=540-680)
- **Building exterior**: (x=310-560, y=620-770) — large cutscene building
- **Nicelander faces**: small heads scattered in the building area
- **Ralph action sprites**: bottom-left (x=0-450, y=610-960)
- **Font rows**: very bottom (x=0-500, y=968-1024) — 8px row height, characters ~7-8px wide

Create the sprite_data.py with ALL coordinates mapped. Below is the structure — the implementer must fill in exact pixel coordinates using the sprite viewer tool for each entry:

```python
SPRITES = {
    # Building tiles
    "wall_brick": [(0, 0, 208, 112)],
    "wall_section_lower": [(0, 112, 208, 112)],
    "window_intact": [],       # Map each window state from the atlas
    "window_cracked": [],
    "window_broken": [],
    "window_frame": [],
    "shutter_left": [],
    "shutter_right": [],
    "niceland_sign": [],
    "ledge": [],

    # Felix animations — each list has multiple frames
    "felix_idle_right": [],
    "felix_idle_left": [],
    "felix_walk_right": [],
    "felix_walk_left": [],
    "felix_climb_up": [],
    "felix_climb_down": [],
    "felix_hammer_right": [],
    "felix_hammer_left": [],
    "felix_hammer_up": [],
    "felix_stunned": [],
    "felix_celebrate": [],
    "felix_head": [],          # For lives display

    # Ralph animations
    "ralph_idle": [],
    "ralph_smash": [],
    "ralph_throw": [],
    "ralph_climb": [],
    "ralph_fall": [],
    "ralph_face": [],

    # Hazards and items
    "brick_falling": [],
    "bird_right": [],
    "bird_left": [],
    "pie": [],

    # UI elements
    "title_logo": [],
    "medal_bronze": [],
    "medal_silver": [],
    "medal_gold": [],

    # Cutscene elements
    "building_exterior": [],
    "tree_left": [],
    "tree_right": [],
    "cloud": [],
    "ralph_cutscene_idle": [],
    "ralph_cutscene_smash": [],
    "nicelander_head": [],
}

# Font definition — 4 color rows of bitmap characters
# Each row starts at a y-offset, characters are 8px wide, 8px tall
# Character order matches ASCII from '!' (0x21) onward
FONT_ROWS = {
    0: {"y": 968, "char_width": 8, "char_height": 8, "start_x": 8},
    1: {"y": 976, "char_width": 8, "char_height": 8, "start_x": 8},
    2: {"y": 984, "char_width": 8, "char_height": 8, "start_x": 8},
    3: {"y": 992, "char_width": 8, "char_height": 8, "start_x": 8},
}

# Hammer effect sprites (from hammer0-3.png)
HAMMER_SPRITES = {
    "hammer_swing": [],        # Hammer animation frames
    "repair_sparkle": [],      # Repair effect animation (flowers at bottom of sheet)
}
```

**CRITICAL**: The implementer MUST use the sprite viewer to fill in every `[]` with actual `(x, y, w, h)` tuples from the atlas. Run the viewer, zoom in on each sprite region, drag-select, and copy the printed coordinates. This is the most time-intensive step of the entire project — budget 30-60 minutes.

- [ ] **Step 4: Verify sprite loading works**

Add a temporary test to `main.py`'s `PlaceholderScene` that loads and displays a sprite:

```python
class PlaceholderScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        from sprite_sheet import SpriteSheet
        self.sprites = SpriteSheet()

    def draw(self, screen):
        screen.fill(BLACK)
        try:
            building = self.sprites.get_sprite("wall_brick", 0, 0)
            screen.blit(building, (50, 50))
        except (KeyError, IndexError) as e:
            font = pygame.font.SysFont("monospace", 16)
            text = font.render(str(e), True, WHITE)
            screen.blit(text, (10, 10))
```

Run: `cd src && python3 main.py`
Expected: Building tile sprite renders at (50, 50).

- [ ] **Step 5: Commit**

```bash
git add src/sprite_sheet.py src/sprite_data.py tools/sprite_viewer.py src/main.py
git commit -m "feat: sprite sheet system with atlas loader, data definitions, and viewer tool"
```

---

### Task 4: Font Renderer

**Files:**
- Create: `src/font_renderer.py`

**Interfaces:**
- Consumes: `SpriteSheet.get_sprite()`, `FONT_ROWS` from `sprite_data.py`
- Produces: `FontRenderer` class with `render_text(text, color_row=0) -> pygame.Surface`

- [ ] **Step 1: Create `src/font_renderer.py`**

```python
import pygame
from sprite_data import FONT_ROWS


class FontRenderer:
    def __init__(self, sprite_sheet, palette=0):
        self._sprite_sheet = sprite_sheet
        self._palette = palette
        self._char_cache = {}
        self._build_char_map()

    def _build_char_map(self):
        ascii_chars = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ/1"
        for row_idx, row_info in FONT_ROWS.items():
            atlas = self._sprite_sheet._get_atlas(self._palette)
            y = row_info["y"]
            cw = row_info["char_width"]
            ch = row_info["char_height"]
            start_x = row_info["start_x"]
            for i, char in enumerate(ascii_chars):
                x = start_x + i * cw
                try:
                    surface = atlas.subsurface(pygame.Rect(x, y, cw, ch)).copy()
                    self._char_cache[(char, row_idx)] = surface
                except ValueError:
                    pass

    def render_text(self, text, color_row=0):
        text = text.upper()
        row_info = FONT_ROWS.get(color_row, FONT_ROWS[0])
        cw = row_info["char_width"]
        ch = row_info["char_height"]

        surface = pygame.Surface((len(text) * cw, ch), pygame.SRCALPHA)
        for i, char in enumerate(text):
            glyph = self._char_cache.get((char, color_row))
            if glyph:
                surface.blit(glyph, (i * cw, 0))
        return surface
```

- [ ] **Step 2: Test font rendering in PlaceholderScene**

Update `PlaceholderScene` in `main.py`:

```python
class PlaceholderScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        from sprite_sheet import SpriteSheet
        from font_renderer import FontRenderer
        self.sprites = SpriteSheet()
        self.font = FontRenderer(self.sprites)

    def draw(self, screen):
        screen.fill(BLACK)
        text_surface = self.font.render_text("FIX-IT FELIX JR", color_row=0)
        scaled = pygame.transform.scale(text_surface,
            (text_surface.get_width() * 3, text_surface.get_height() * 3))
        rect = scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2))
        screen.blit(scaled, rect)
```

Run: `cd src && python3 main.py`
Expected: "FIX-IT FELIX JR" rendered in bitmap font, scaled 3x, centered on screen.

- [ ] **Step 3: Commit**

```bash
git add src/font_renderer.py src/main.py
git commit -m "feat: bitmap font renderer using atlas font rows"
```

---

### Task 5: Sound Manager

**Files:**
- Create: `src/sound_manager.py`

**Interfaces:**
- Produces: `SoundManager` class with `play_sfx(name)`, `play_music(name, loop=True)`, `stop_music()`

- [ ] **Step 1: Create `src/sound_manager.py`**

```python
import os
import pygame
from constants import ASSET_DIR

SOUND_MAP = {
    "hammer_hit": "sound3",
    "hammer_hit_alt": "sound6",
    "jump": "sound5",
    "window_break": "sound20",
    "hammer_extended": "sound17",   # Ghidra-confirmed: index 0x11 = hammer extended anim
    "pie_pickup": "sound16",
    "ralph_grunt": "sound1",
    "window_fixed": "sound4",
    "felix_catchphrase": "sound2",
    "ralph_catchphrase": "sound0",
    "super_felix": "sound25",
    "section_clear": "sound22",
    "score_bonus": "sound23",
    "pie_throw": "sound18",
    "level_transition": "sound13",
    "ralph_falling": "sound29",
    "bonus_life": "sound10",
    "game_over": "sound21",
    "menu_select": "sound26",
    "menu_confirm": "sound27",
    "bonus_score_alt": "sound28",
    "felix_move": "sound15",        # Ghidra-confirmed: index 0x0F = state transition/movement
    "death": "sound19",             # Ghidra-confirmed: index 0x13 = death/game over
}

MUSIC_MAP = {
    "cutscene_intro": "sound11",
    "level_clear": "sound12",
    "high_score": "sound24",
    "gameplay_a": "sound7",
    "gameplay_b": "sound8",
    "title": "sound9",
    "extended": "sound14",
}


class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        self._sounds = {}
        self._load_sounds()

    def _load_sounds(self):
        for name, filename in SOUND_MAP.items():
            path = os.path.join(ASSET_DIR, f"{filename}.wav")
            if os.path.exists(path):
                self._sounds[name] = pygame.mixer.Sound(path)

    def play_sfx(self, name):
        sound = self._sounds.get(name)
        if sound:
            sound.play()

    def play_music(self, name, loop=True):
        filename = MUSIC_MAP.get(name)
        if not filename:
            return
        path = os.path.join(ASSET_DIR, f"{filename}.wav")
        if os.path.exists(path):
            pygame.mixer.music.load(path)
            loops = -1 if loop else 0
            pygame.mixer.music.play(loops)

    def stop_music(self):
        pygame.mixer.music.stop()

    def set_sfx_volume(self, volume):
        for sound in self._sounds.values():
            sound.set_volume(volume)

    def set_music_volume(self, volume):
        pygame.mixer.music.set_volume(volume)
```

- [ ] **Step 2: Verify sounds load without error**

Add a quick sound test in `PlaceholderScene.on_enter()`:

```python
    def on_enter(self):
        from sound_manager import SoundManager
        self.sound = SoundManager()
        self.sound.play_music("title")
```

Run: `cd src && python3 main.py`
Expected: Title music plays. No load errors.

- [ ] **Step 3: Commit**

```bash
git add src/sound_manager.py src/main.py
git commit -m "feat: sound manager with SFX and music mapping for all 30 WAV files"
```

---

### Task 6: Building & Window Grid

**Files:**
- Create: `src/entities/building.py`
- Create: `src/entities/__init__.py`

**Interfaces:**
- Consumes: `SpriteSheet`, `FontRenderer`
- Produces: `WindowState` enum (`INTACT, CRACKED, BROKEN`)
- Produces: `Building` class with `damage_window(col, row)`, `repair_window(col, row, is_super=False) -> (repaired, fully_fixed)`, `is_section_clear() -> bool`, `is_level_clear() -> bool`, `get_window_state(col, row) -> WindowState`, `advance_section()`, `reset_for_level(level)`, `draw(screen, sprite_sheet, palette)`

- [ ] **Step 1: Create `src/entities/__init__.py`** (empty file)

- [ ] **Step 2: Create `src/entities/building.py`**

```python
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
        if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
            self._current_grid[row][col].damage()

    def repair_window(self, col, row, is_super=False):
        if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
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
        y = GRID_TOP + (GRID_ROWS - 1 - row) * WINDOW_SPACING_Y
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
        for row in range(GRID_ROWS):
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
```

- [ ] **Step 3: Write unit tests for window state logic**

Create: `tests/test_building.py`

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from entities.building import WindowSlot, WindowState, Building


def test_window_damage_cycle():
    w = WindowSlot()
    assert w.state == WindowState.INTACT
    w.damage()
    assert w.state == WindowState.CRACKED
    w.damage()
    assert w.state == WindowState.BROKEN
    w.damage()
    assert w.state == WindowState.BROKEN


def test_window_repair_cycle():
    w = WindowSlot()
    w.state = WindowState.BROKEN
    repaired, fully_fixed = w.repair()
    assert repaired is True
    assert fully_fixed is False
    assert w.state == WindowState.CRACKED
    repaired, fully_fixed = w.repair()
    assert repaired is True
    assert fully_fixed is True
    assert w.state == WindowState.INTACT


def test_window_repair_intact_noop():
    w = WindowSlot()
    repaired, fully_fixed = w.repair()
    assert repaired is False
    assert fully_fixed is False


def test_window_super_repair():
    w = WindowSlot()
    w.state = WindowState.BROKEN
    repaired, fully_fixed = w.repair(is_super=True)
    assert repaired is True
    assert fully_fixed is True
    assert w.state == WindowState.INTACT


def test_section_clear():
    b = Building()
    b.reset_for_level(1)
    assert not b.is_section_clear()
    for row in b._current_grid:
        for window in row:
            window.state = WindowState.INTACT
    assert b.is_section_clear()


def test_level_progression():
    b = Building()
    b.reset_for_level(1)
    for _ in range(SECTIONS_PER_LEVEL):
        for row in b._current_grid:
            for window in row:
                window.state = WindowState.INTACT
        b.advance_section()
    assert b.is_level_clear()


if __name__ == "__main__":
    from entities.building import SECTIONS_PER_LEVEL
    test_window_damage_cycle()
    test_window_repair_cycle()
    test_window_repair_intact_noop()
    test_window_super_repair()
    test_section_clear()
    test_level_progression()
    print("All building tests passed!")
```

- [ ] **Step 4: Run tests**

Run: `python3 tests/test_building.py`
Expected: "All building tests passed!"

- [ ] **Step 5: Commit**

```bash
git add src/entities/__init__.py src/entities/building.py tests/test_building.py
git commit -m "feat: building and window grid with damage/repair state machine"
```

---

### Task 7: Felix Entity

**Files:**
- Create: `src/entities/felix.py`

**Interfaces:**
- Consumes: `Building.get_window_pixel_pos()`, `Building.repair_window()`, `InputHandler`, `SpriteSheet`, `SoundManager`
- Produces: `FelixState` enum, `Felix` class with `tick(input_handler, building, sound)`, `draw(screen, sprite_sheet, palette, building)`, `stun()`, `activate_super()`, `add_score(points)`, `col`, `row`, `state`, `score`, `lives`, `is_super`, `is_alive`

**Design note:** Ghidra pass 3 confirmed Felix uses **float-based velocity/acceleration physics**, not grid snapping. Movement between windows is animated with velocity that accelerates toward max speed, then snaps to position on arrival. Stun is **position-based recovery** (knockback above screen), not a simple timer. Jump uses a **parabolic arc** trajectory. The state machine uses function-pointer dispatch internally; we model it with an enum + if/elif chain.

- [ ] **Step 1: Create `src/entities/felix.py`**

```python
import math
import enum
import pygame
from input_handler import Action
from entities.building import GRID_COLS, WINDOW_WIDTH, WINDOW_HEIGHT
from constants import (
    INITIAL_LIVES, BONUS_LIFE_THRESHOLD, SUPER_DURATION_TICKS,
    FELIX_MAX_HORIZONTAL_SPEED, FELIX_INITIAL_VERTICAL_VEL,
    FELIX_JUMP_INITIAL_X_VEL, FELIX_JUMP_ARC_DIVISOR,
    FELIX_FALL_TERMINAL_VEL, FELIX_HAMMER_START_OFFSET,
    FELIX_STUN_KNOCKBACK_Y, FELIX_HORIZONTAL_ACCEL,
    FELIX_VERTICAL_MOVE_RATE, FELIX_GRAVITY_ACCEL, HAMMER_ANIM_RATE,
)


class FelixState(enum.Enum):
    IDLE = 0
    WALK_HORIZONTAL = 1
    WALK_VERTICAL = 3
    JUMPING = 4
    HAMMERING = 5
    HAMMER_EXTENDED = 6
    FALLING = 7
    STUNNED = 8
    DYING = 9
    DEATH_HANDLER = 10
    CELEBRATING = 11


class Felix:
    def __init__(self):
        self.col = 2
        self.row = 0
        self.state = FelixState.IDLE
        self.facing_right = True
        self.score = 0
        self.lives = INITIAL_LIVES
        self.is_super = False

        self._pos_x = 0.0
        self._pos_y = 0.0
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._target_x = 0.0
        self._target_y = 0.0
        self._move_target_col = 0
        self._move_target_row = 0

        self._state_ticks = 0
        self._super_ticks = 0
        self._hammer_offset = 0.0
        self._hammer_phase = 0
        self._anim_frame = 0
        self._next_bonus_at = BONUS_LIFE_THRESHOLD
        self._pos_initialized = False

    @property
    def is_alive(self):
        return self.lives > 0

    def _init_pos(self, building):
        if not self._pos_initialized:
            px, py = building.get_window_pixel_pos(self.col, self.row)
            self._pos_x = float(px)
            self._pos_y = float(py)
            self._pos_initialized = True

    def reset_position(self):
        self.col = 2
        self.row = 0
        self.state = FelixState.IDLE
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._state_ticks = 0
        self._pos_initialized = False

    def add_score(self, points):
        self.score += points
        while self.score >= self._next_bonus_at:
            self.lives += 1
            self._next_bonus_at += BONUS_LIFE_THRESHOLD

    def stun(self, sound=None):
        if self.is_super or self.state == FelixState.STUNNED:
            return
        self.state = FelixState.STUNNED
        self._state_ticks = 0
        self._vel_x = 0.0
        self._vel_y = 0.0
        self.lives -= 1

    def activate_super(self, sound=None):
        self.is_super = True
        self._super_ticks = 0
        if sound:
            sound.play_sfx("super_felix")

    def tick(self, input_handler, building, sound=None):
        self._init_pos(building)
        self._anim_frame = (self._anim_frame + 1) % 4

        if self.is_super:
            self._super_ticks += 1
            if self._super_ticks >= SUPER_DURATION_TICKS:
                self.is_super = False

        if self.state == FelixState.IDLE:
            self._tick_idle(input_handler, building, sound)
        elif self.state == FelixState.WALK_HORIZONTAL:
            self._tick_walk_horizontal(building, sound)
        elif self.state == FelixState.WALK_VERTICAL:
            self._tick_walk_vertical(building, sound)
        elif self.state == FelixState.JUMPING:
            self._tick_jumping(building, sound)
        elif self.state == FelixState.HAMMERING:
            self._tick_hammering(building, sound)
        elif self.state == FelixState.HAMMER_EXTENDED:
            self._tick_hammer_extended(building, sound)
        elif self.state == FelixState.FALLING:
            self._tick_falling(building, sound)
        elif self.state == FelixState.STUNNED:
            self._tick_stunned(building, sound)
        elif self.state == FelixState.DYING:
            self._tick_dying(sound)
        elif self.state == FelixState.DEATH_HANDLER:
            self._tick_death_handler(sound)

    def _tick_idle(self, input_handler, building, sound):
        self._snap_to_grid(building)

        if input_handler.is_just_pressed(Action.JUMP):
            self.state = FelixState.HAMMERING
            self._state_ticks = 0
            self._hammer_offset = FELIX_HAMMER_START_OFFSET
            self._hammer_phase = 0
            if sound:
                sound.play_sfx("hammer_hit")
            return

        dx, dy = 0, 0
        if input_handler.is_just_pressed(Action.LEFT):
            dx = -1
            self.facing_right = False
        elif input_handler.is_just_pressed(Action.RIGHT):
            dx = 1
            self.facing_right = True
        elif input_handler.is_just_pressed(Action.UP):
            dy = -1
        elif input_handler.is_just_pressed(Action.DOWN):
            dy = 1

        if dx != 0:
            new_col = self.col + dx
            if 0 <= new_col < GRID_COLS:
                self._move_target_col = new_col
                self._move_target_row = self.row
                tx, ty = building.get_window_pixel_pos(new_col, self.row)
                self._target_x = float(tx)
                self._target_y = float(ty)
                self._vel_x = FELIX_MAX_HORIZONTAL_SPEED * dx
                self._vel_y = 0.0
                self.state = FelixState.WALK_HORIZONTAL
                self._state_ticks = 0
                if sound:
                    sound.play_sfx("felix_move")
        elif dy != 0:
            new_row = self.row + dy
            if 0 <= new_row < building.current_rows:
                self._move_target_col = self.col
                self._move_target_row = new_row
                tx, ty = building.get_window_pixel_pos(self.col, new_row)
                self._target_x = float(tx)
                self._target_y = float(ty)
                self._vel_x = 0.0
                self._vel_y = FELIX_VERTICAL_MOVE_RATE * dy
                self.state = FelixState.JUMPING
                self._state_ticks = 0
                if sound:
                    sound.play_sfx("jump")

    def _tick_walk_horizontal(self, building, sound):
        self._pos_x += self._vel_x
        arrived = (self._vel_x > 0 and self._pos_x >= self._target_x) or \
                  (self._vel_x < 0 and self._pos_x <= self._target_x)
        if arrived:
            self.col = self._move_target_col
            self.row = self._move_target_row
            self._snap_to_grid(building)
            self.state = FelixState.IDLE
            self._vel_x = 0.0

    def _tick_walk_vertical(self, building, sound):
        self._pos_y += self._vel_y
        arrived = (self._vel_y > 0 and self._pos_y >= self._target_y) or \
                  (self._vel_y < 0 and self._pos_y <= self._target_y)
        if arrived:
            self.col = self._move_target_col
            self.row = self._move_target_row
            self._snap_to_grid(building)
            self.state = FelixState.IDLE
            self._vel_y = 0.0

    def _tick_jumping(self, building, sound):
        dist_x = self._target_x - self._pos_x
        dist_y = self._target_y - self._pos_y
        dist = math.sqrt(dist_x * dist_x + dist_y * dist_y)

        if dist < FELIX_VERTICAL_MOVE_RATE:
            self.col = self._move_target_col
            self.row = self._move_target_row
            self._snap_to_grid(building)
            self.state = FelixState.IDLE
            self._vel_x = 0.0
            self._vel_y = 0.0
            return

        speed = FELIX_VERTICAL_MOVE_RATE
        self._pos_x += (dist_x / dist) * speed
        self._pos_y += (dist_y / dist) * speed

    def _tick_hammering(self, building, sound):
        self._state_ticks += 1
        self._hammer_offset += HAMMER_ANIM_RATE
        if self._hammer_offset >= 0.0:
            self._hammer_phase = 1
            self.state = FelixState.HAMMER_EXTENDED
            self._state_ticks = 0
            if sound:
                sound.play_sfx("hammer_extended")

    def _tick_hammer_extended(self, building, sound):
        self._state_ticks += 1
        if self._state_ticks >= 2:
            repaired, fully_fixed = building.repair_window(
                self.col, self.row, is_super=self.is_super
            )
            if repaired:
                self.add_score(100)
                if sound:
                    sound.play_sfx("hammer_hit")
            if fully_fixed:
                self.add_score(500)
                if sound:
                    sound.play_sfx("window_fixed")
            self.state = FelixState.IDLE

    def _tick_falling(self, building, sound):
        self._vel_y += FELIX_GRAVITY_ACCEL
        if self._vel_y > FELIX_FALL_TERMINAL_VEL:
            self._vel_y = FELIX_FALL_TERMINAL_VEL
        self._pos_y += self._vel_y
        px, py = building.get_window_pixel_pos(self.col, self.row)
        if self._pos_y >= py:
            self._snap_to_grid(building)
            self.state = FelixState.IDLE
            self._vel_y = 0.0

    def _tick_stunned(self, building, sound):
        self._state_ticks += 1
        target_x, target_y = building.get_window_pixel_pos(self.col, self.row)
        if self._state_ticks == 1:
            self._pos_y = FELIX_STUN_KNOCKBACK_Y
        if self._state_ticks < 4:
            return
        fall_speed = 8.0
        self._pos_y -= fall_speed
        if self._pos_y <= target_y:
            self._snap_to_grid(building)
            if self.lives <= 0:
                self.state = FelixState.DYING
                self._state_ticks = 0
            else:
                self.state = FelixState.IDLE

    def _tick_dying(self, sound):
        self._state_ticks += 1
        if self._state_ticks >= 4:
            self.state = FelixState.DEATH_HANDLER
            self._state_ticks = 0

    def _tick_death_handler(self, sound):
        if self.lives <= 0:
            if sound:
                sound.play_sfx("death")
            return
        if sound:
            sound.play_sfx("felix_move")
        self.reset_position()

    def _snap_to_grid(self, building):
        px, py = building.get_window_pixel_pos(self.col, self.row)
        self._pos_x = float(px)
        self._pos_y = float(py)

    def get_pixel_pos(self, building):
        self._init_pos(building)
        return int(self._pos_x), int(self._pos_y)

    def draw(self, screen, sprite_sheet, palette, building):
        px, py = self.get_pixel_pos(building)

        sprite_name = "felix_idle_right"
        frame = 0

        if self.state == FelixState.STUNNED:
            sprite_name = "felix_stunned"
        elif self.state in (FelixState.HAMMERING, FelixState.HAMMER_EXTENDED):
            sprite_name = "felix_hammer_right" if self.facing_right else "felix_hammer_left"
        elif self.state in (FelixState.WALK_HORIZONTAL, FelixState.WALK_VERTICAL,
                            FelixState.JUMPING):
            sprite_name = "felix_walk_right" if self.facing_right else "felix_walk_left"
            frame = self._anim_frame % max(sprite_sheet.get_frame_count(sprite_name), 1)
        elif self.state == FelixState.CELEBRATING:
            sprite_name = "felix_celebrate"
        else:
            sprite_name = "felix_idle_right" if self.facing_right else "felix_idle_left"

        try:
            sprite = sprite_sheet.get_sprite(sprite_name, frame, palette)
            offset_x = (WINDOW_WIDTH - sprite.get_width()) // 2
            offset_y = WINDOW_HEIGHT - sprite.get_height()
            screen.blit(sprite, (px + offset_x, py + offset_y))
        except (KeyError, IndexError):
            color = (255, 255, 0) if self.is_super else (0, 100, 255)
            pygame.draw.rect(screen, color, (px + 4, py + 4, 16, 24))
            pygame.draw.circle(screen, (255, 200, 150), (px + 12, py + 6), 5)

        if self.is_super:
            flash = pygame.Surface((16, 24), pygame.SRCALPHA)
            flash.fill((255, 255, 100, 80))
            screen.blit(flash, (px + 4, py + 4))
```

- [ ] **Step 2: Write unit tests for Felix logic**

Create: `tests/test_felix.py`

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()

from entities.felix import Felix, FelixState
from constants import BONUS_LIFE_THRESHOLD
from entities.building import Building


class MockInput:
    def __init__(self):
        self._just = set()

    def is_just_pressed(self, action):
        return action in self._just

    def is_pressed(self, action):
        return action in self._just


def test_initial_state():
    f = Felix()
    assert f.col == 2
    assert f.row == 0
    assert f.state == FelixState.IDLE
    assert f.lives == 10
    assert f.score == 0


def test_stun_costs_life():
    f = Felix()
    b = Building()
    b.reset_for_level(1)
    f.tick(MockInput(), b)
    f.stun()
    assert f.state == FelixState.STUNNED
    assert f.lives == 9


def test_super_prevents_stun():
    f = Felix()
    f.activate_super()
    f.stun()
    assert f.state != FelixState.STUNNED
    assert f.lives == 10


def test_score_bonus_life():
    f = Felix()
    initial = f.lives
    f.add_score(BONUS_LIFE_THRESHOLD)
    assert f.lives == initial + 1


def test_move_within_bounds():
    from input_handler import Action
    f = Felix()
    b = Building()
    b.reset_for_level(1)
    inp = MockInput()
    inp._just = {Action.RIGHT}
    f.tick(inp, b)
    assert f.state == FelixState.WALK_HORIZONTAL


def test_move_blocked_at_edge():
    from input_handler import Action
    f = Felix()
    f.col = 0
    b = Building()
    b.reset_for_level(1)
    inp = MockInput()
    inp._just = {Action.LEFT}
    f.tick(inp, b)
    assert f.state == FelixState.IDLE


def test_hammer_triggers():
    from input_handler import Action
    f = Felix()
    b = Building()
    b.reset_for_level(1)
    inp = MockInput()
    inp._just = {Action.JUMP}
    f.tick(inp, b)
    assert f.state == FelixState.HAMMERING


def test_stun_recovery():
    f = Felix()
    b = Building()
    b.reset_for_level(1)
    f.tick(MockInput(), b)
    f.stun()
    for _ in range(20):
        f.tick(MockInput(), b)
    assert f.state == FelixState.IDLE


if __name__ == "__main__":
    test_initial_state()
    test_stun_costs_life()
    test_super_prevents_stun()
    test_score_bonus_life()
    test_move_within_bounds()
    test_move_blocked_at_edge()
    test_hammer_triggers()
    test_stun_recovery()
    print("All Felix tests passed!")
```

- [ ] **Step 3: Run tests**

Run: `python3 tests/test_felix.py`
Expected: "All Felix tests passed!"

- [ ] **Step 4: Commit**

```bash
git add src/entities/felix.py tests/test_felix.py
git commit -m "feat: Felix entity with state machine, movement, hammering, and scoring"
```

---

### Task 8: Ralph & Bricks

**Files:**
- Create: `src/entities/ralph.py`
- Create: `src/entities/brick.py`

**Interfaces:**
- Consumes: `Building`, `Felix`, `SpriteSheet`, `SoundManager`
- Produces: `Ralph` class with `update(dt, felix, building, sound) -> list[Brick]`, `draw(screen, sprite_sheet, palette)`
- Produces: `Brick` class with `update(dt) -> bool` (returns True when off-screen), `draw(screen, sprite_sheet, palette)`, `get_grid_hit(building) -> (col, row) | None`, `hits_felix(felix, building) -> bool`

- [ ] **Step 1: Create `src/entities/brick.py`**

```python
import pygame
from entities.building import GRID_COLS, GRID_ROWS, WINDOW_WIDTH, WINDOW_HEIGHT


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
        for row in range(GRID_ROWS):
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
```

- [ ] **Step 2: Create `src/entities/ralph.py`**

```python
import random
import pygame
from entities.brick import Brick
from entities.building import GRID_COLS, WINDOW_SPACING_X, GRID_LEFT


from entities.brick import BRICK_FALL_SPEEDS, BRICK_DRIFT_SPEED

MAX_BRICKS = 4  # Ghidra-confirmed: 4 brick entity pairs


class Ralph:
    def __init__(self):
        self.x = 90           # Ghidra: Ralph Y position = 0x5A (90)
        self.y = 10
        self.throw_ticks = 0
        self.throw_interval_ticks = 12
        self.aim_chance = 0.2
        self.bricks_per_throw = 1
        self._anim_frame = 0
        self._is_throwing = False
        self._throw_anim_ticks = 0

    def configure_for_level(self, level):
        self.throw_interval_ticks = max(3, 12 - (level - 1))
        self.aim_chance = min(0.2 + (level - 1) * 0.05, 0.6)
        self.bricks_per_throw = min(1 + (level - 1) // 3, 4)

    def tick(self, felix, building, sound=None):
        """Called once per game tick (250ms)."""
        new_bricks = []

        self._anim_frame = (self._anim_frame + 1) % 2

        if self._is_throwing:
            self._throw_anim_ticks += 1
            if self._throw_anim_ticks >= 2:
                self._is_throwing = False

        self.throw_ticks += 1
        if self.throw_ticks >= self.throw_interval_ticks:
            self.throw_ticks = 0
            self._is_throwing = True
            self._throw_anim_ticks = 0
            if sound:
                sound.play_sfx("ralph_grunt")

            for _ in range(self.bricks_per_throw):
                if random.random() < self.aim_chance:
                    target_col = felix.col
                else:
                    target_col = random.randint(0, GRID_COLS - 1)

                brick_x = GRID_LEFT + target_col * WINDOW_SPACING_X + 20
                fall_speed = random.choice(BRICK_FALL_SPEEDS)
                drift = random.uniform(-BRICK_DRIFT_SPEED, BRICK_DRIFT_SPEED)
                brick = Brick(brick_x, self.y + 40, fall_speed, drift)
                new_bricks.append(brick)

        return new_bricks

    def draw(self, screen, sprite_sheet, palette):
        sprite_name = "ralph_throw" if self._is_throwing else "ralph_idle"
        try:
            sprite = sprite_sheet.get_sprite(sprite_name, self._anim_frame, palette)
            screen.blit(sprite, (int(self.x), int(self.y)))
        except (KeyError, IndexError):
            color = (200, 50, 50) if self._is_throwing else (180, 80, 80)
            pygame.draw.rect(screen, color, (int(self.x), int(self.y), 60, 70))
            pygame.draw.circle(screen, (220, 160, 120),
                (int(self.x) + 30, int(self.y) + 15), 15)
```

- [ ] **Step 3: Commit**

```bash
git add src/entities/brick.py src/entities/ralph.py
git commit -m "feat: Ralph NPC with brick throwing and Brick entity with collision detection"
```

---

### Task 9: Bird & Pie Entities

**Files:**
- Create: `src/entities/bird.py`
- Create: `src/entities/pie.py`

**Interfaces:**
- Produces: `Bird` class with `update(dt) -> bool`, `hits_felix(felix, building) -> bool`, `draw(screen, sprite_sheet, palette)`
- Produces: `Pie` class with `update(dt) -> bool`, `collected_by_felix(felix, building) -> bool`, `draw(screen, sprite_sheet, palette)`

- [ ] **Step 1: Create `src/entities/bird.py`**

```python
import pygame
from entities.building import WINDOW_WIDTH, WINDOW_HEIGHT
from constants import GAME_WIDTH


BIRD_SPEED_X = 2.2   # Ghidra pass 3: _DAT_00416b94


class Bird:
    def __init__(self, row, from_left, speed, building):
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
```

- [ ] **Step 2: Create `src/entities/pie.py`**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add src/entities/bird.py src/entities/pie.py
git commit -m "feat: Bird hazard and Pie power-up entities"
```

---

### Task 10: Game Scene — Core Gameplay Integration

**Files:**
- Create: `src/scenes/__init__.py`
- Create: `src/scenes/game_scene.py`
- Modify: `src/main.py` — replace PlaceholderScene with GameScene

**Interfaces:**
- Consumes: All entities (`Felix`, `Ralph`, `Building`, `Brick`, `Bird`, `Pie`), `SpriteSheet`, `SoundManager`, `FontRenderer`, `InputHandler`
- Produces: `GameScene` class that orchestrates gameplay

- [ ] **Step 1: Create `src/scenes/__init__.py`** (empty file)

- [ ] **Step 2: Create `src/scenes/game_scene.py`**

```python
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
from entities.building import Building, GRID_COLS, GRID_ROWS
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
        self._bird_timer = 0.0
        self._bird_interval = 8.0
        self._bird_from_left = True
        self._pie_timer = 0.0
        self._pie_interval = 30.0
        self._section_clear_timer = 0.0
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
        self._bird_timer = 0.0
        self._pie_timer = 0.0
        self._is_section_clearing = False

        bird_level_threshold = 2
        self._bird_interval = max(4.0, 8.0 - (self.level - bird_level_threshold) * 0.5)
        self._pie_interval = max(20.0, 30.0 - (self.level - 1) * 1.0)

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
                bird_row = random.randint(0, GRID_ROWS - 1)
                bird_speed = min(100 + (self.level - 2) * 10, 150)
                bird = Bird(bird_row, self._bird_from_left, bird_speed, self.building)
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
            pie_row = random.randint(0, GRID_ROWS - 1)
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
        self._section_clear_timer = 0.0
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
```

- [ ] **Step 3: Update `main.py` to launch GameScene**

Replace the PlaceholderScene import and usage in `main.py`:

```python
from scenes.game_scene import GameScene
```

And in `main()`:

```python
    scene_manager.push(GameScene(scene_manager))
```

Remove the PlaceholderScene class entirely.

- [ ] **Step 4: Manually verify**

Run: `cd src && python3 main.py`
Expected: Game launches with building grid visible, Felix can move with arrow keys, press Space to hammer, Ralph throws bricks, bricks break windows, Felix gets stunned on hit. Fallback rectangles render if sprite data isn't populated yet — that's fine. Core gameplay loop should be functional.

- [ ] **Step 5: Commit**

```bash
git add src/scenes/__init__.py src/scenes/game_scene.py src/main.py
git commit -m "feat: GameScene with full gameplay loop integrating all entities"
```

---

### Task 11: Title Scene

**Files:**
- Create: `src/scenes/title_scene.py`
- Modify: `src/main.py` — start with TitleScene instead of GameScene

**Interfaces:**
- Consumes: `SpriteSheet`, `SoundManager`, `FontRenderer`, `InputHandler`
- Produces: `TitleScene` class that transitions to GameScene on START/JUMP

- [ ] **Step 1: Create `src/scenes/title_scene.py`**

```python
import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer


class TitleScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._blink_timer = 0.0
        self._show_press_start = True

    def on_enter(self):
        self.sound.play_music("title")

    def on_exit(self):
        self.sound.stop_music()

    def handle_input(self, input_handler):
        if (input_handler.is_just_pressed(Action.START) or
                input_handler.is_just_pressed(Action.JUMP)):
            self.sound.play_sfx("menu_confirm")
            from scenes.game_scene import GameScene
            self.manager.replace(GameScene(self.manager))

    def update(self, dt):
        self._blink_timer += dt
        if self._blink_timer >= 0.5:
            self._blink_timer = 0.0
            self._show_press_start = not self._show_press_start

    def draw(self, screen):
        screen.fill(BLACK)

        # All coordinates in 240x320 internal space — no scaling needed
        try:
            logo = self.sprites.get_sprite("title_logo", 0, 0)
            rect = logo.get_rect(center=(GAME_WIDTH // 2, 80))
            screen.blit(logo, rect)
        except (KeyError, IndexError):
            title = self.font.render_text("FIX-IT FELIX JR", color_row=0)
            rect = title.get_rect(center=(GAME_WIDTH // 2, 80))
            screen.blit(title, rect)

        copyright_text = self.font.render_text("@TOBIKOMI COMPANY 1982", color_row=1)
        rect = copyright_text.get_rect(center=(GAME_WIDTH // 2, 130))
        screen.blit(copyright_text, rect)

        if self._show_press_start:
            start_text = self.font.render_text("PRESS START", color_row=0)
            rect = start_text.get_rect(center=(GAME_WIDTH // 2, 250))
            screen.blit(start_text, rect)
```

- [ ] **Step 2: Update `main.py` to start with TitleScene**

```python
from scenes.title_scene import TitleScene
```

In `main()`:

```python
    scene_manager.push(TitleScene(scene_manager))
```

- [ ] **Step 3: Manually verify**

Run: `cd src && python3 main.py`
Expected: Title screen shows with blinking "PRESS START". Title music plays. Pressing Enter or Space transitions to the game.

- [ ] **Step 4: Commit**

```bash
git add src/scenes/title_scene.py src/main.py
git commit -m "feat: title scene with logo, blinking prompt, and music"
```

---

### Task 12: Game Over & High Score Scenes

**Files:**
- Create: `src/scenes/game_over_scene.py`
- Create: `src/scenes/high_score_scene.py`

**Interfaces:**
- Produces: `GameOverScene(manager, final_score)` — shows "GAME OVER", transitions to HighScoreScene
- Produces: `HighScoreScene(manager, final_score)` — initials entry, persists scores, transitions to TitleScene

- [ ] **Step 1: Create `src/scenes/game_over_scene.py`**

```python
import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer


class GameOverScene(Scene):
    def __init__(self, manager, final_score):
        super().__init__(manager)
        self.final_score = final_score
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._timer = 0.0

    def on_enter(self):
        self.sound.play_sfx("game_over")

    def update(self, dt):
        self._timer += dt
        if self._timer >= 3.0:
            from scenes.high_score_scene import HighScoreScene
            self.manager.replace(HighScoreScene(self.manager, self.final_score))

    def draw(self, screen):
        screen.fill(BLACK)

        game_over = self.font.render_text("GAME OVER", color_row=0)
        scaled = pygame.transform.scale(game_over,
            (game_over.get_width() * 4, game_over.get_height() * 4))
        rect = scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 - 30))
        screen.blit(scaled, rect)

        score = self.font.render_text(f"SCORE {self.final_score:06d}", color_row=1)
        scaled_score = pygame.transform.scale(score,
            (score.get_width() * 2, score.get_height() * 2))
        rect = scaled_score.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 + 40))
        screen.blit(scaled_score, rect)
```

- [ ] **Step 2: Create `src/scenes/high_score_scene.py`**

```python
import json
import os
import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK, PROJECT_ROOT
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer

SCORES_FILE = os.path.join(PROJECT_ROOT, "scores.dat")
MAX_SCORES = 5                # Ghidra-confirmed: 5 entries
INITIALS_LENGTH = 3           # Ghidra-confirmed: 3 chars
# Ghidra-confirmed: 38 characters including space, A-Z, 0-9, period
LETTER_OPTIONS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."


def load_scores():
    if os.path.exists(SCORES_FILE):
        try:
            with open(SCORES_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_scores(scores):
    with open(SCORES_FILE, "w") as f:
        json.dump(scores, f, indent=2)


class HighScoreScene(Scene):
    def __init__(self, manager, final_score=0):
        super().__init__(manager)
        self.final_score = final_score
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self.scores = load_scores()

        self._is_entering = self._qualifies()
        self._initials = ["A", "A", "A"]
        self._cursor = 0
        self._letter_index = 0
        self._display_timer = 0.0

    def _qualifies(self):
        if self.final_score <= 0:
            return False
        if len(self.scores) < MAX_SCORES:
            return True
        return self.final_score > self.scores[-1]["score"]

    def on_enter(self):
        self.sound.play_music("high_score", loop=False)

    def on_exit(self):
        self.sound.stop_music()

    def handle_input(self, input_handler):
        if self._is_entering:
            if input_handler.is_just_pressed(Action.UP):
                self._letter_index = (self._letter_index - 1) % len(LETTER_OPTIONS)
                self._initials[self._cursor] = LETTER_OPTIONS[self._letter_index]
                self.sound.play_sfx("menu_select")
            elif input_handler.is_just_pressed(Action.DOWN):
                self._letter_index = (self._letter_index + 1) % len(LETTER_OPTIONS)
                self._initials[self._cursor] = LETTER_OPTIONS[self._letter_index]
                self.sound.play_sfx("menu_select")
            elif input_handler.is_just_pressed(Action.JUMP):
                self._cursor += 1
                self._letter_index = 0
                self.sound.play_sfx("menu_confirm")
                if self._cursor >= INITIALS_LENGTH:
                    self._save_score()
                    self._is_entering = False
        else:
            if (input_handler.is_just_pressed(Action.START) or
                    input_handler.is_just_pressed(Action.JUMP)):
                from scenes.title_scene import TitleScene
                self.manager.replace(TitleScene(self.manager))

    def update(self, dt):
        if not self._is_entering:
            self._display_timer += dt
            if self._display_timer >= 10.0:
                from scenes.title_scene import TitleScene
                self.manager.replace(TitleScene(self.manager))

    def _save_score(self):
        name = "".join(self._initials)
        self.scores.append({"name": name, "score": self.final_score})
        self.scores.sort(key=lambda s: s["score"], reverse=True)
        self.scores = self.scores[:MAX_SCORES]
        save_scores(self.scores)

    def draw(self, screen):
        screen.fill(BLACK)

        header = self.font.render_text("HIGH SCORES", color_row=0)
        header_scaled = pygame.transform.scale(header,
            (header.get_width() * 3, header.get_height() * 3))
        rect = header_scaled.get_rect(center=(GAME_WIDTH // 2, 40))
        screen.blit(header_scaled, rect)

        if self._is_entering:
            prompt = self.font.render_text("ENTER YOUR INITIALS", color_row=1)
            p_scaled = pygame.transform.scale(prompt,
                (prompt.get_width() * 2, prompt.get_height() * 2))
            rect = p_scaled.get_rect(center=(GAME_WIDTH // 2, 90))
            screen.blit(p_scaled, rect)

            initials_str = " ".join(self._initials)
            initials = self.font.render_text(initials_str, color_row=0)
            i_scaled = pygame.transform.scale(initials,
                (initials.get_width() * 3, initials.get_height() * 3))
            rect = i_scaled.get_rect(center=(GAME_WIDTH // 2, 130))
            screen.blit(i_scaled, rect)

        col_header = self.font.render_text("NAME      SCORE", color_row=1)
        ch_scaled = pygame.transform.scale(col_header,
            (col_header.get_width() * 2, col_header.get_height() * 2))
        screen.blit(ch_scaled, (120, 170))

        for i, entry in enumerate(self.scores[:MAX_SCORES]):
            name = entry["name"].ljust(3)
            score_str = str(entry["score"]).rjust(8)
            line = f"{name}      {score_str}"
            text = self.font.render_text(line, color_row=0)
            t_scaled = pygame.transform.scale(text,
                (text.get_width() * 2, text.get_height() * 2))
            screen.blit(t_scaled, (120, 200 + i * 24))
```

- [ ] **Step 3: Manually verify**

Run: `cd src && python3 main.py`
Expected: Play until game over. "GAME OVER" screen appears for 3 seconds, then high score entry. Use UP/DOWN to change letters, SPACE to confirm each. After 3 initials, score saves to `scores.dat` and shows the table. Pressing START returns to title.

- [ ] **Step 4: Commit**

```bash
git add src/scenes/game_over_scene.py src/scenes/high_score_scene.py
git commit -m "feat: game over and high score scenes with initials entry and JSON persistence"
```

---

### Task 13: Level Clear & Cutscene Scenes

**Files:**
- Create: `src/scenes/level_clear_scene.py`
- Create: `src/scenes/cutscene_scene.py`
- Modify: `src/scenes/game_scene.py` — transition to LevelClearScene on level clear, and start via CutsceneScene
- Modify: `src/scenes/title_scene.py` — transition to CutsceneScene instead of GameScene

**Interfaces:**
- Produces: `LevelClearScene(manager, level, score, sprites, sound, font)` — medal display, transitions back to GameScene with next level
- Produces: `CutsceneScene(manager)` — intro sequence, transitions to GameScene

- [ ] **Step 1: Create `src/scenes/level_clear_scene.py`**

```python
import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer


class LevelClearScene(Scene):
    def __init__(self, manager, level, score):
        super().__init__(manager)
        self.level = level
        self.score = score
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._timer = 0.0

    def on_enter(self):
        self.sound.play_music("level_clear", loop=False)

    def on_exit(self):
        self.sound.stop_music()

    def _medal_name(self):
        if self.level <= 3:
            return "medal_bronze"
        elif self.level <= 7:
            return "medal_silver"
        return "medal_gold"

    def _medal_label(self):
        if self.level <= 3:
            return "BRONZE"
        elif self.level <= 7:
            return "SILVER"
        return "GOLD"

    def update(self, dt):
        self._timer += dt
        if self._timer >= 5.0:
            from scenes.game_scene import GameScene
            game = GameScene(self.manager)
            game.level = self.level + 1
            game.felix.score = self.score
            self.manager.replace(game)

    def handle_input(self, input_handler):
        if input_handler.is_just_pressed(Action.JUMP) and self._timer >= 1.0:
            from scenes.game_scene import GameScene
            game = GameScene(self.manager)
            game.level = self.level + 1
            game.felix.score = self.score
            self.manager.replace(game)

    def draw(self, screen):
        screen.fill(BLACK)

        clear_text = self.font.render_text("LEVEL CLEAR!", color_row=0)
        scaled = pygame.transform.scale(clear_text,
            (clear_text.get_width() * 3, clear_text.get_height() * 3))
        rect = scaled.get_rect(center=(GAME_WIDTH // 2, 100))
        screen.blit(scaled, rect)

        try:
            medal = self.sprites.get_sprite(self._medal_name(), 0, 0)
            medal_scaled = pygame.transform.scale(medal,
                (medal.get_width() * 2, medal.get_height() * 2))
            rect = medal_scaled.get_rect(center=(GAME_WIDTH // 2, 240))
            screen.blit(medal_scaled, rect)
        except (KeyError, IndexError):
            medal_label = self.font.render_text(self._medal_label() + " MEDAL", color_row=1)
            m_scaled = pygame.transform.scale(medal_label,
                (medal_label.get_width() * 2, medal_label.get_height() * 2))
            rect = m_scaled.get_rect(center=(GAME_WIDTH // 2, 240))
            screen.blit(m_scaled, rect)

        score_text = self.font.render_text(f"SCORE {self.score:06d}", color_row=1)
        s_scaled = pygame.transform.scale(score_text,
            (score_text.get_width() * 2, score_text.get_height() * 2))
        rect = s_scaled.get_rect(center=(GAME_WIDTH // 2, 350))
        screen.blit(s_scaled, rect)
```

- [ ] **Step 2: Create `src/scenes/cutscene_scene.py`**

```python
import pygame
from scene_manager import Scene
from constants import GAME_WIDTH, GAME_HEIGHT, BLACK, SKY_BLUE
from input_handler import Action
from sprite_sheet import SpriteSheet
from sound_manager import SoundManager
from font_renderer import FontRenderer


CUTSCENE_STEPS = [
    {"duration": 2.0, "text": "", "sprite": "building_exterior"},
    {"duration": 2.5, "text": "HEY. YOU MOVED MY STUMP!", "sprite": "ralph_cutscene_idle"},
    {"duration": 2.5, "text": "I'M GONNA WRECK IT!", "sprite": "ralph_cutscene_smash"},
    {"duration": 2.0, "text": "FIX IT FELIX!", "sprite": None},
    {"duration": 2.0, "text": "I CAN FIX IT!", "sprite": None},
]


class CutsceneScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.sprites = SpriteSheet()
        self.sound = SoundManager()
        self.font = FontRenderer(self.sprites)
        self._step = 0
        self._timer = 0.0

    def on_enter(self):
        self.sound.play_music("cutscene_intro", loop=False)

    def on_exit(self):
        self.sound.stop_music()

    def handle_input(self, input_handler):
        if input_handler.is_just_pressed(Action.JUMP) or input_handler.is_just_pressed(Action.START):
            self._start_game()

    def update(self, dt):
        self._timer += dt
        if self._step < len(CUTSCENE_STEPS):
            if self._timer >= CUTSCENE_STEPS[self._step]["duration"]:
                self._timer = 0.0
                self._step += 1
                if self._step >= len(CUTSCENE_STEPS):
                    self._start_game()

    def _start_game(self):
        from scenes.game_scene import GameScene
        self.manager.replace(GameScene(self.manager))

    def draw(self, screen):
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
            scaled = pygame.transform.scale(text,
                (text.get_width() * 2, text.get_height() * 2))
            rect = scaled.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 + 80))
            screen.blit(scaled, rect)
```

- [ ] **Step 3: Update GameScene to transition to LevelClearScene**

In `src/scenes/game_scene.py`, replace the `_advance_level` method:

```python
    def _advance_level(self):
        self.sound.stop_music()
        from scenes.level_clear_scene import LevelClearScene
        self.manager.replace(LevelClearScene(
            self.manager, self.level, self.felix.score))
```

- [ ] **Step 4: Update TitleScene to go through CutsceneScene**

In `src/scenes/title_scene.py`, update the `handle_input` transition:

```python
        if (input_handler.is_just_pressed(Action.START) or
                input_handler.is_just_pressed(Action.JUMP)):
            self.sound.play_sfx("menu_confirm")
            from scenes.cutscene_scene import CutsceneScene
            self.manager.replace(CutsceneScene(self.manager))
```

- [ ] **Step 5: Manually verify the full game flow**

Run: `cd src && python3 main.py`
Expected: Title → Cutscene (skippable) → Game → Section clear messages → Level clear with medal → Next level → Game Over → High Scores → Title. Full loop works.

- [ ] **Step 6: Commit**

```bash
git add src/scenes/level_clear_scene.py src/scenes/cutscene_scene.py src/scenes/game_scene.py src/scenes/title_scene.py
git commit -m "feat: level clear and cutscene scenes, complete game flow loop"
```

---

### Task 14: Sprite Data Population

This task is about using the sprite viewer tool to fill in all the empty sprite coordinate lists in `sprite_data.py`. This is a manual process that requires visual inspection of the atlas.

**Files:**
- Modify: `src/sprite_data.py`

**Interfaces:**
- Produces: Complete `SPRITES` dictionary with all bounding boxes filled in

- [ ] **Step 1: Run the sprite viewer and systematically map each region**

Run: `python3 tools/sprite_viewer.py`

Work through the atlas region by region:

1. **Building tiles** (top-left, ~x=0-208, y=0-224): Zoom in and select wall sections, window variants (intact blue windows, cracked windows, broken/dark windows), shutters, ledges
2. **Windows and signs** (top-center, ~x=208-480, y=0-160): Niceland signs above windows, different window frame styles
3. **Title logo** (~x=200-400, y=100-160): The "FIX-IT FELIX JR" logo block
4. **Felix sprites** (rows at ~y=160-310, x=0-500): Zoom in on each small figure, select bounding boxes. Group by animation: idle (standing), walking (multi-frame), climbing, hammering, stunned, celebrating
5. **Ralph sprites** (~y=310-600, x=0-450): Large figures — idle, smashing, throwing, climbing, falling
6. **Medals** (top-right ~x=500-800, y=0-120): Bronze, silver, gold medals with ribbons
7. **Hazards** — birds (small, in the building area), pie (look for pie/cake shape)
8. **Cutscene elements** — building exterior (~x=310-560, y=620-770), trees, clouds, text overlays
9. **Font rows** — verify the character width and positions at y=968+

For each sprite, drag-select in the viewer and copy the printed `(x, y, w, h)` tuple.

- [ ] **Step 2: Update `src/sprite_data.py` with all coordinates**

Fill in every empty list with the mapped coordinates. Each animation gets multiple frames as separate tuples in the list.

- [ ] **Step 3: Run the game and visually verify sprites render correctly**

Run: `cd src && python3 main.py`
Expected: All placeholder rectangles replaced with actual sprite graphics. Felix animates when moving. Ralph has idle/throw poses. Building renders with real window tiles.

- [ ] **Step 4: Iterate — fix any misaligned or incorrectly-sized sprites**

Re-run the sprite viewer, adjust coordinates, re-test. Repeat until all sprites display correctly.

- [ ] **Step 5: Commit**

```bash
git add src/sprite_data.py
git commit -m "feat: complete sprite coordinate definitions for all atlas regions"
```

---

### Task 15: Polish — Difficulty Tuning, Sound Refinement, and Final Touches

**Files:**
- Modify: `src/entities/ralph.py` — verify difficulty scaling
- Modify: `src/scenes/game_scene.py` — tune gameplay feel
- Modify: `src/sound_manager.py` — refine sound mappings after listening

- [ ] **Step 1: Listen to all sound files and verify mappings**

Play each sound file individually:

```bash
for i in $(seq 0 29); do echo "=== sound$i ==="; afplay Data/sound$i.wav & sleep 2; kill %1 2>/dev/null; done
```

Compare what you hear against the mapping in `sound_manager.py`. Swap any misassigned sounds.

- [ ] **Step 2: Tune difficulty progression**

Play through levels 1-5. All timing is in ticks (250ms each). Adjust in `ralph.py`'s `configure_for_level()`:
- `throw_interval_ticks`: level 1 = 12 ticks (3 sec), decrease per level, min 3 ticks
- Brick fall speeds are Ghidra-verified: -1.5 to -2.2 px/tick (randomly selected per brick)
- Brick drift: ±1.7 px/tick (Ghidra-verified)
- `aim_chance`: shouldn't feel unfair even at high values
- Max 4 bricks on screen (Ghidra-confirmed, hardcoded)
- `bricks_per_throw`: starts at 1, increases every 3 levels up to 4

Also adjust in `game_scene.py`:
- `_bird_interval_ticks`: birds at 2.2 px/tick horizontal (Ghidra-verified), shouldn't overwhelm
- `_pie_interval_ticks`: pies should feel like a reward, not constant (~120 ticks = 30 sec)

Verify Felix movement feels right:
- Horizontal walk at 2.0 px/tick (Ghidra-confirmed) — should cross one column in ~20 ticks (5 sec)
- Vertical jump movement at ~4.0 px/tick (estimated) — tune until row transitions feel snappy
- Stun knockback to y=480 then falls back — should feel like a visible penalty, ~10 ticks total

Remember: game runs at 4 ticks/second. A "fast" throw interval of 3 ticks = 0.75 real seconds.

- [ ] **Step 3: Add Super Felix visual indicator**

In `src/entities/felix.py`'s `draw()` method, when `self.is_super` is True, add a visual effect — either blit a hammer sparkle overlay from the hammer sheets or tint the sprite:

```python
        if self.is_super:
            flash_surface = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
            flash_surface.fill((255, 255, 100, 80))
            screen.blit(flash_surface, (px + offset_x, py + offset_y))
```

- [ ] **Step 4: Add window caption with score**

In `src/main.py`, inside the main loop after updating:

```python
        pygame.display.set_caption(f"Fix-It Felix Jr.")
```

- [ ] **Step 5: Final playthrough and commit**

Run: `cd src && python3 main.py`
Expected: Complete game flow feels polished. Sound effects match actions. Difficulty ramps appropriately. Super Felix has visual feedback. All scenes transition smoothly.

```bash
git add -A
git commit -m "feat: difficulty tuning, sound refinement, and visual polish"
```
