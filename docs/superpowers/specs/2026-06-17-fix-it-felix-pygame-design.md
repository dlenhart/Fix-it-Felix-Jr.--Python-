# Fix-It Felix Jr. — Pygame Recreation Design Spec

## Overview

Faithful recreation of the Fix-It Felix Jr. arcade game (from Wreck-It Ralph) as a Python/Pygame application. Uses the original sprite sheets, sound effects, and visual assets extracted from the Windows executable. Constants and mechanics verified via Ghidra decompilation of the original binary (see `ghidra-analysis-findings.md` for raw data).

## Goals & Constraints

- **Faithful recreation**: match the original arcade game — same mechanics, scoring, grid layout, timing model
- **Single player only**: multiplayer deferred to a future phase
- **240×320 internal resolution** (confirmed by Ghidra): render at 240×320 and scale up to display window (e.g. 3× = 720×960)
- **250ms fixed-step game logic** (confirmed by Ghidra): game advances 4 ticks per second, rendering interpolates between ticks at display refresh rate
- **Manual sprite extraction**: precise bounding boxes defined for every sprite region in the atlas
- **Keyboard + gamepad input**: unified input abstraction
- **Python 3 + Pygame**: no other dependencies

## Assets Inventory

### Sprite Atlases (1024×1024 RGBA PNGs)

- `felix0.png` through `felix4.png` — five palette variants. All share identical sprite positions, different palette colors. Each uses a specific color key for transparency:
  - `felix0`: yellow (255,255,0,255)
  - `felix1`: yellow + green (0,255,0,255)
  - `felix2`: white (255,255,255,255)
  - `felix3`: yellow + cyan (0,255,255,255)
  - `felix4`: special palette handling (skips indices 0xF5-0xF7)

- Atlas contents:
  - Felix animation frames: idle, walk (two directions), jump/move, hammer (initial + extended), stunned, dead/dying, celebrating
  - Wreck-It Ralph: idle, smash, throw, fall, various expressions, cutscene poses
  - Building tiles: brick walls, intact/cracked/broken windows (two variants each), shutters, frames, Niceland sign
  - UI: title logo "FIX-IT FELIX JR", medals (bronze/silver/gold), text overlays
  - Nicelander heads/faces
  - Construction vehicles, trees, clouds (decorative)
  - Bitmap font: multiple color rows at the bottom of each sheet

### Hammer Effect Sheets (1024×1024 RGBA PNGs)

- `hammer0.png` through `hammer3.png` — repair sparkle/flower effects:
  - `hammer0`: red (255,0,0,255)
  - `hammer1`: green (0,255,0,255)
  - `hammer2`: white (255,255,255,255)
  - `hammer3`: cyan (0,255,255,255)

### Other Assets

- `texture2.bmp` — 1024×1024 building texture (BMP format, loaded with BGRA→RGBA conversion and alpha inversion)
- `FixItFelixBootLoader.bmp` / `FixItFelixBootLoader180.bmp` — 640×480 splash screens
- `sound0.wav` through `sound29.wav` — 30 sound effects and music tracks (all 44100 Hz)
- `Controls.log` — binary grid layout data (20-byte records, flag values {1, 2, 4, 8, 64})

## Architecture: Scene-Based State Machine

### Project Structure

```
Fix-it/
├── Data/                    # Existing assets (untouched)
│   ├── felix0-4.png
│   ├── hammer0-3.png
│   ├── texture2.bmp
│   ├── sound0-29.wav
│   └── Controls.log
├── FixItFelixBootLoader.bmp
├── FixItFelixBootLoader180.bmp
├── src/
│   ├── main.py              # Entry point, init pygame, run SceneManager
│   ├── constants.py         # Screen size, FPS, colors, enums, tick rate
│   ├── scene_manager.py     # Scene stack, transitions
│   ├── input_handler.py     # Keyboard + gamepad abstraction
│   ├── sprite_sheet.py      # Atlas loading, region extraction
│   ├── sprite_data.py       # Bounding box definitions for all sprites
│   ├── sound_manager.py     # Sound loading, mapping, playback
│   ├── font_renderer.py     # Bitmap font from sprite sheet
│   ├── scenes/
│   │   ├── title_scene.py
│   │   ├── cutscene_scene.py
│   │   ├── game_scene.py    # Main gameplay
│   │   ├── level_clear_scene.py
│   │   ├── game_over_scene.py
│   │   └── high_score_scene.py
│   └── entities/
│       ├── felix.py
│       ├── ralph.py
│       ├── building.py      # Window grid, section types, damage states
│       ├── brick.py
│       ├── bird.py
│       └── pie.py
```

### Core Loop (main.py)

- Initialize Pygame display at 720×960 (3× scale of 240×320)
- Create a 240×320 internal surface for all game rendering
- Scale internal surface to display surface each frame
- Render at 60 FPS for smooth display, but **advance game logic in fixed 250ms ticks** (accumulator pattern)
- Main loop:
  1. `dt = clock.tick(60) / 1000.0`
  2. `tick_accumulator += dt`
  3. While `tick_accumulator >= 0.25`: `scene_manager.tick(input_handler)`, `tick_accumulator -= 0.25`
  4. `scene_manager.draw(internal_surface)`
  5. Scale `internal_surface` to display, `pygame.display.flip()`

### SceneManager

Maintains a scene stack:

- `push(scene)` — add scene on top (e.g. pause overlay)
- `replace(scene)` — swap current scene (e.g. title → game)
- `pop()` — return to previous scene
- Only the top scene receives `tick()` and `handle_input()`
- `draw()` can cascade down the stack for overlay effects

## Rendering Model

### Internal vs Display Resolution

The original game operates on a **240×320 coordinate system** (portrait orientation — taller than wide). All sprite positions, grid coordinates, and collision checks use these coordinates.

Display window can be any multiple:
- 2× = 480×640
- 3× = 720×960 (recommended default)
- 4× = 960×1280

Scaling uses nearest-neighbor filtering to preserve pixel art crispness.

### Fixed-Step Timing (250ms Ticks)

All game timing is measured in **ticks**, where 1 tick = 250ms real time. The game advances 4 ticks per second.

The display counter "TIME LEFT" divides the tick counter by 60 to get displayed "seconds" — meaning **1 displayed second = 60 ticks = 15 real seconds**.

Key timing values (all in ticks):
- High score entry timeout: 1800 ticks (30 displayed, 450 real seconds)
- New game countdown: 300 ticks (75 real seconds)
- High score display: 900 ticks (225 real seconds)
- D-pad repeat delay: 20 ticks (5 real seconds)

## Sprite System

### Sprite Data (sprite_data.py)

Python dictionary mapping logical sprite names to atlas bounding boxes `(x, y, width, height)`. Grouped by category:

- **Felix animations**: idle, walk_a, walk_b, jump/move, hammer_initial, hammer_extended, stunned, dead, celebrate — each a list of `(x, y, w, h)` frames
- **Ralph animations**: idle, smash, throw, climb, fall — frame lists
- **Building tiles**: wall_brick, window_intact_a, window_intact_b, window_cracked_a, window_cracked_b, window_broken_a, window_broken_b, window_frame, shutters, niceland_sign
- **Hazards & items**: brick_falling, bird, pie
- **UI**: medal_bronze, medal_silver, medal_gold, title_logo

### SpriteSheet Class (sprite_sheet.py)

- Loads an atlas PNG as a `pygame.Surface` with `convert_alpha()`
- `get_sprite(name, frame=0, palette=0)` — returns cropped Surface
- `palette` param selects which atlas (felix0-4.png) for level color variants
- Caches extracted surfaces: one crop per unique `(name, frame, palette)` tuple

### Font Renderer (font_renderer.py)

- Parses the bitmap font rows at the bottom of each sprite sheet
- Characters are monospaced (~8px wide), full ASCII printable set
- `render_text(text, color_row=0)` → returns a Surface
- Used for all in-game text: score, level, "GAME OVER", high scores, etc.

## Building & Window Grid

### Structure (Confirmed by Ghidra)

Each level section has a **5-column × 5-7 row** grid of window positions. The original game has **5 different section types** with varying row counts and window row configurations:

| Section Type | Rows | Window Row Pattern |
|-------------|------|--------------------|
| 0 | 7 | empty, empty, normal_A, empty, empty |
| 1 | 7 | empty, empty, normal_B, empty, empty |
| 2 | 6 | brick_A, brick_A, brick_B, brick_A, brick_A |
| 3 | 7 | brick_A, brick_A, brick_B, brick_A, brick_A |
| 4 | special | 5 sub-rows with explicit entity setup |

Each section structure is 740 bytes (0x2E4) internally, with a row stride of 140 bytes (0x8C).

### Window States

```
INTACT → CRACKED → BROKEN    (damage from Ralph's bricks)
BROKEN → CRACKED → INTACT    (repair from Felix's hammer)
```

Two visual variants exist for each state (A and B), used by different row types.

- Felix hammers a BROKEN window twice (broken→cracked→intact)
- Felix hammers a CRACKED window once (cracked→intact)
- Super Felix repairs in one hit regardless of state

### Building Class (building.py)

- Manages sections and their window grids
- Tracks current section and section type
- 32 window entity slots per player (confirmed by Ghidra)
- Key methods:
  - `is_section_clear()` — all windows in current section INTACT
  - `get_window_at(col, row)` — WindowSlot at Felix's position
  - `damage_window(col, row)` — brick hits window
  - `repair_window(col, row)` — Felix hammers window

### Level Progression

- Different section types are assigned per level (mapping in the difficulty config)
- Palette swaps via felix0-4.png (cycling through 5 variants)
- After level 10, behavior changes (confirmed by `if (level < 10)` branch in binary)

## Entities

### Felix (felix.py) — Player Character

- **Grid position**: `(col, row)` on current building section, **5 columns (0-4)**
- **State machine** (11 states confirmed by Ghidra):

| State | Name | Description |
|-------|------|-------------|
| 0 | IDLE | Standing still |
| 1 | WALK_A | Walking direction A |
| 3 | WALK_B | Walking direction B |
| 4 | MOVING | Jumping/moving to grid position |
| 5 | HAMMERING | Initial hammer swing |
| 6 | HAMMER_EXTENDED | Extended hammer animation |
| 7 | FALLING | Falling/sliding |
| 8 | STUNNED | Hit by brick or bird |
| 9 | DYING | Death animation |
| 10 | DEATH_HANDLER | Check lives, transition |

- **Movement**: on input, plays jump/climb animation while tweening between grid positions. Blocked at building edges (col 0 and col 4).
- **Hammering**: JUMP pressed while stationary → state 5 (initial swing) → state 6 (extended) → repair window one step.
- **Stunned**: hit by brick or bird → state 8, checks position relative to row center to determine flip direction. Loses one life.
- **Death handler** (state 10): if lives == 0, plays sound 0x13 (19) and sets game-over flag. If lives > 0, plays sound 0x0F (15) and respawns.
- **Starting position**: bottom-center of each building section (col=2, row=0)
- **Super Felix**: pie collected → invincible, one-hit repairs, sparkle overlay
- **Lives**: starts with **10** (confirmed by Ghidra: `_DAT_00424258 = 10`)
- **Scoring**: +100 per hammer repair, +500 when window reaches fully INTACT (confirmed by strings)

### Ralph (ralph.py) — NPC Antagonist

- Positioned at top of current building section
- **4 brick entity pairs** per level (front + back, confirmed by Ghidra: loop count = 4)
- Periodic brick throwing on a timer
- Climbing animation between sections

### Brick (brick.py) — Falling Hazard

- **4 bricks maximum on screen** (confirmed: 4 entity pairs allocated in level setup)
- Spawned by Ralph, falls downward
- Collision with window: damages window one step, brick disappears
- Collision with Felix: stuns Felix (unless Super)
- Fixed positions relative to building: offsets of ±64 pixels from center (0x40)

### Bird (bird.py) — Horizontal Hazard

- Flies horizontally at specific window row height, entering from either side
- Appears at higher levels
- Collision with Felix: stuns him (unless Super)

### Pie (pie.py) — Power-Up

- Dropped by Nicelander from window above at intervals
- Sits on window ledge briefly before disappearing
- Felix collects by moving to that position
- Triggers Super Felix state

### Collision Detection

Grid-based coordinate checks for most interactions. All coordinates in the 240×320 space.

## Scenes & Game Flow

The original game has **11 game states** (confirmed by Ghidra), which we map to scenes:

| Original State | Our Scene | Description |
|---------------|-----------|-------------|
| 0, 10 | TitleScene | Title/attract mode |
| 9 | InstructionScene | Instructions/demo |
| 1 | (GameScene init) | Level start |
| 3 | GameScene | Active gameplay |
| 5 | LevelClearScene | Level complete |
| 4 | (GameScene) | Player switch (2P, deferred) |
| 7 | (transition) | New game start |
| 8 | HighScoreScene | High score entry |
| 2 | HighScoreScene | High score display |
| 6 | (skipped) | Network setup (not implementing) |

```
TitleScene → CutsceneScene → GameScene ⟷ LevelClearScene
                                ↓
                          GameOverScene → HighScoreScene → TitleScene
```

### TitleScene

- "FIX-IT FELIX JR" logo, "©TOBIKOMI COMPANY 1982"
- "HIGH SCORE" display and "1UP" in bitmap font
- "CREDITS" display (format: `CREDITS %02d`)
- Blinking "PRESS START" prompt
- Title music (sound9, 15.68s, looped)
- START/JUMP → CutsceneScene
- Hides 9 UI elements on entry (confirmed by state 10)

### CutsceneScene

- Intro sequence: Nicelanders in building, Ralph arrives, text overlays
- Large Ralph sprites, building exterior, Nicelander faces
- Cutscene music (sound11, 3.56s)
- Auto-advances to GameScene, or JUMP to skip

### GameScene

- Main gameplay loop managing all entities, building, scoring, lives
- HUD: 5-digit score at specific positions (x=240 to x=328, y=318, spacing=22), level number, lives
- Section-based building progression per level
- Section clear → "YOU FIXED IT!" animation, scroll to next section
- All sections clear → LevelClearScene
- Lives hit 0 → GameOverScene
- Gameplay music loops (sound7/sound8)
- `DAT_00418064 = 0x6F` (111) set on gameplay start

### LevelClearScene

- Medal ceremony: bronze (early), silver (mid), gold (late levels)
- Victory jingle (sound12, 6.38s)
- Score tally animation
- Auto-advances → GameScene with next level

### GameOverScene

- "GAME OVER" in bitmap font (single player)
- "GAME OVER PLAYER %d" for 2P mode (deferred)
- Game over sound (sound 0x13 = sound19, confirmed by Ghidra)
- Final score display
- Brief pause → HighScoreScene

### HighScoreScene

- "HIGH SCORES" header, "NAME SCORE" table
- **5 entries** (confirmed), **3-character initials** (confirmed), **20-byte records** (confirmed)
- Character set: `" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."` (38 characters, confirmed by Ghidra)
- Default initials: "AAA"
- Entry timer: **1800 ticks** (displayed as 30 via `/ 60` divisor, ~450 real seconds)
- D-pad repeat delay: **20 ticks** (5 real seconds)
- Display timeout: **900 ticks** (225 real seconds)
- Score format: `%06d` (6-digit zero-padded)
- Scores persisted to `scores.dat` in JSON format
- After entry/display → TitleScene

## Input System (input_handler.py)

### Unified Action Abstraction

`ActionType` enum: `UP, DOWN, LEFT, RIGHT, JUMP, START, QUIT`

### Original Input Mapping (from Ghidra)

The original uses bit-masked input:
- Direction bits: `0x0F` (bits 0-3 for up/down/left/right)
- Action bits: `0x60` (bits 5-6 for jump/action)
- Mouse button: bits 4-5 (`0x30`)

### Keyboard Mapping

- Arrow keys → movement
- Space → JUMP/HAMMER
- Enter → START
- Escape → QUIT

### Gamepad Mapping

- D-pad / left stick → movement
- Button 0 (A/X) → JUMP/HAMMER
- Button 7 (Start) → START

### Query Modes

- `is_pressed(action)` — currently held (continuous)
- `is_just_pressed(action)` — rising edge only (for discrete grid movement and hammer swings)

## Sound System (sound_manager.py)

### Sound Loading (from Ghidra)

- All 30 sounds loaded sequentially as `sound0` through `sound29`
- Batch load size: 30 (0x1E, confirmed)
- If a sound fails to load, it clones the previous sound entry
- WAV parsing: supports 8-bit, 16-bit, 24-bit audio, mono and stereo
- Internal mixing at 44100 Hz (0xAC44)
- Default volume: 256 (0x100)

### Sound Mapping (Partial Correction from Ghidra)

Binary confirms these specific indices:
- Sound 0x0F (15): state transition / movement sound
- Sound 0x11 (17): hammer extended animation
- Sound 0x13 (19): death / game over

Remaining mappings (duration-based estimates, to be verified by listening):

| Event | File | Duration | Type |
|-------|------|----------|------|
| Hammer hit/fix | sound3 | 0.32s | SFX |
| Hammer hit (alt) | sound6 | 0.32s | SFX |
| Jump | sound5 | 0.48s | SFX |
| Window break | sound20 | 0.42s | SFX |
| State transition / movement | sound15 | 0.47s | SFX |
| Pie pickup | sound16 | 0.43s | SFX |
| Ralph grunt | sound1 | 0.60s | SFX |
| Hammer extended | sound17 | 0.60s | SFX |
| Window fully fixed | sound4 | 0.95s | SFX |
| Felix catchphrase | sound2 | 1.06s | SFX |
| Ralph catchphrase | sound0 | 1.18s | SFX |
| Super Felix active | sound25 | 1.93s | SFX |
| Section clear | sound22 | 1.85s | SFX |
| Score/bonus | sound23 | 1.03s | SFX |
| Nicelander pie throw | sound18 | 1.52s | SFX |
| Level transition | sound13 | 1.75s | SFX |
| Death / game over | sound19 | 1.52s | SFX |
| Ralph falling | sound29 | 1.95s | SFX |
| Bonus life | sound10 | 2.77s | Jingle |
| Game over jingle | sound21 | 2.73s | Jingle |
| Intro cutscene | sound11 | 3.56s | Music |
| Level clear / victory | sound12 | 6.38s | Music |
| High score / results | sound24 | 8.05s | Music |
| Gameplay music A | sound7 | 10.97s | Music |
| Gameplay music B | sound8 | 11.80s | Music |
| Title music | sound9 | 15.68s | Music |
| Extended music | sound14 | 22.59s | Music |
| Menu select | sound26 | 0.53s | SFX |
| Menu confirm | sound27 | 0.58s | SFX |
| Bonus score (alt) | sound28 | 1.03s | SFX |

### Playback

- Music tracks: `pygame.mixer.music` with looping
- SFX: `pygame.mixer.Sound` on mixer channels
- API: `play_sfx(name)`, `play_music(name, loop=True)`, `stop_music()`

## Difficulty Tuning

The exact difficulty scaling formula is in callback functions not fully decompiled. The following are starting estimates, with confirmed anchor points:

| Parameter | Level 1 | Level 5 | Level 10+ |
|-----------|---------|---------|-----------|
| Section type assignment | Types 0-1 | Types 2-3 | Type 4 |
| Brick throw interval | ~12 ticks | ~6 ticks | ~3 ticks |
| Max bricks on screen | 4 (confirmed) | 4 | 4 |
| Initial broken windows | 3 | 8 | 12 |

Note: all timing values in ticks (250ms each). Level 10 has a confirmed behavioral branch.

## Persistence

- `scores.dat` — high score table in JSON format (5 entries, 3-char initials + score)
- Original used `../Save Data/` directory with `Save Game.dat` and `Scores.dat`
- No save/resume for in-progress games (authentic to arcade behavior)

## Key Constants Reference (Confirmed by Ghidra)

| Constant | Value | Source |
|----------|-------|--------|
| Internal resolution | 240×320 | DIB section setup |
| Bits per pixel | 24 | DIB section setup |
| Game tick rate | 250ms (4 Hz) | SetTimer(0xFA) |
| Initial lives | 10 | `_DAT_00424258 = 10` |
| Windows per row | 5 | `puVar3[0x13] = 5` |
| Rows per section | 6-7 | `(type != 2) + 6` |
| Section types | 5 (0-4) | Switch statement |
| Section struct size | 740 bytes | `malloc(0x2E4)` |
| Row stride | 140 bytes | `0x8C` |
| Entity record size | 32 bytes | `malloc(0x20)` |
| Player state size | 3876 bytes | Stride `0xF24` |
| Max brick entities | 4 pairs | Loop count = 4 |
| Window entities/player | 32 | Loop count = 0x20 |
| High score entries | 5 | Loop bound |
| HS initials length | 3 | Position max = 2 |
| HS entry size | 20 bytes | Stride 0x14 |
| HS character set | 38 chars | " A-Z 0-9 ." |
| HS entry timer | 1800 ticks | `0x708` |
| HS display timer | 900 ticks | Direct assignment |
| Time display divisor | 60 ticks | `/ 0x3C` |
| Score format | %06d | sprintf |
| Felix textures | 5 (0-4) | Load loop |
| Hammer textures | 4 (0-3) | Load loop |
| Sound files | 30 (0-29) | Batch 0x1E |
| Audio mixing rate | 44100 Hz | `0xAC44` |
