# Gameplay Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the game layer (building, windows, Felix's rules, Ralph, bricks, pies, hazards, section and level flow) on the rules decoded in Ghidra pass 4, keeping the engine (loop, input, sound, font, scenes) as is.

**Architecture:** Entities live in **world coordinates** (floors stack upward from y = 320) and draw through a `Camera` that applies the vertical scroll. Exe tables (sprite frames, building pieces) are decoded from the exe into a generated module, so art is addressed by the same ids the game code uses. `GameScene` becomes a thin orchestrator over a **State pattern** of game phases (level start → play → section clear → level end). Each subsystem (bricks, Nicelanders, hazards) is a small manager object the play phase ticks.

**Tech Stack:** Python 3, Pygame, pytest (headless via `SDL_VIDEODRIVER=dummy`).

**Spec:** `docs/superpowers/specs/2026-10-19-gameplay-mechanics-spec.md` (revised 2026-10-21). Evidence behind it: `docs/superpowers/specs/2026-10-19-ghidra-pass4-findings.md`.

## Global Constraints

- Python 3 + Pygame only; no new runtime dependencies.
- Internal resolution 240×320; game logic at 60 ticks/sec through `Scene.tick()`; rendering interpolates with `alpha`.
- Values tagged **[EXE]** in the spec are copied exactly and commented with the exe function or address they come from. Values tagged **[ASSUMED]** are named constants whose comment says `[ASSUMED]`, so they're easy to find and tune.
- Exe tick counts stay raw integers. Estimated durations use `seconds_to_ticks()`.
- All randomness goes through an injected `random.Random`, so tests can seed it. No module-level `random.*` calls in new code.
- **Fail fast:** new drawing code doesn't catch `KeyError`/`IndexError` to draw placeholder rectangles. A missing frame is a bug and must raise.
- **User preferences:** implementation first, tests after (no TDD). **Never run `git commit`**: each task ends with a checkpoint where the user reviews and commits.
- Naming: booleans `is_`/`has_`; no abbreviations beyond universal ones.

## Review Focus

1. **Felix is hit, or a hammer swing completes, outside the play phase** (a brick in flight when the section clears, a bird during the scroll). Nothing may cost a life or score once play has stopped. Test: Task 8.
2. **The window a Nicelander or pie is in gets fixed or the section clears.** The Nicelander and pie must disappear, with no orphan pie left on a fixed or scrolled-away window. Test: Task 9.
3. **The last life is lost during rage, a bounce or invulnerability expiry.** Game over must fire exactly once. Test: Task 8.
4. **Levels past 10.** The config caps at level 10, and level 11+ must not crash. Test: Task 2.
5. **Pause during the scroll or Ralph's climb.** Camera, Ralph and timers freeze, and resume carries on from the same spot. Test: Task 8.

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `tools/decode_exe_tables.py` | new | Reads the two tables from the exe; writes `src/exe_tables.py` and contact sheets |
| `src/exe_tables.py` | new, generated | `SPRITE_FRAMES`, `BUILDING_PIECES` pixel rects, indexed by code id |
| `src/sprite_sheet.py` | modify | `get_frame()`, `get_piece()` by id |
| `src/sprite_data.py` | modify | Named frame/piece ids (`PANE_FRAME_INTACT`, …); drop dead window entries |
| `src/level_config.py` | new | Level table, floor sequences, floor/cell kinds, x positions, piece ids |
| `src/camera.py` | new | Vertical scroll, world → screen, interpolation |
| `src/entities/building.py` | rewrite | `WindowCell`, `Floor`, `Building`: damage, fix, sections, drawing |
| `tools/render_level.py` | new | Renders a whole level's building to PNG for visual checks |
| `src/entities/felix.py` | rework | Cell/floor movement in world coords, accelerating walk, one-swing fix, invulnerability |
| `src/entities/ralph.py` | rewrite | Patrol/pound/rage/pose/climb state machine |
| `src/entities/brick.py` | rewrite | `Brick` + `BrickField` (spawn, fall, Felix hits, window breaks, bounces) |
| `src/entities/nicelander.py` | new | `Nicelander` + `NicelanderDirector` (spawn timer, pie handoff) |
| `src/entities/pie.py` | rewrite | Pie on a cell, collected by Felix |
| `src/entities/hazards.py` | new | Sill-obstacle placement, `Bird`, `DropHazard`, `HazardField` |
| `src/entities/bird.py` | delete | Folded into `hazards.py` |
| `src/scenes/game_phases.py` | new | `LevelStartPhase`, `PlayPhase`, `SectionClearPhase`, `LevelEndPhase` |
| `src/scenes/game_scene.py` | rewrite | Owns state, delegates to the current phase, HUD, pause |
| `src/scenes/level_clear_scene.py` | delete | Replaced by `LevelEndPhase` (the scene also reset lives, which is a bug) |
| `src/scenes/high_score_scene.py` | modify | Default table 15000…4000 |
| `src/constants.py` | modify | New exe constants; remove dead pass-3 misreadings |
| `tests/…` | modify/new | One test file per module, listed in each task |

---

## Phase A — Data foundation

### Task 1: Decode exe tables with the corrected alignment

**Files:**
- Create: `tools/decode_exe_tables.py`, `src/exe_tables.py` (generated, committed)
- Modify: `src/sprite_sheet.py`, `src/sprite_data.py`
- Replace: `docs/ghidra-output/pass4/frame_table.json`, `building_table.json`, `frames_*.png`, `building_table.png` (regenerated, code-numbered)
- Test: `tests/test_exe_tables.py`

**Interfaces:**
- Produces: `exe_tables.SPRITE_FRAMES: tuple[tuple[int, int, int, int], ...]` (216 entries, `(x, y, w, h)` in pixels), `exe_tables.BUILDING_PIECES` (27 entries).
- Produces: `SpriteSheet.get_frame(frame_id: int, palette: int = 0, is_flipped: bool = False) -> pygame.Surface`, `SpriteSheet.get_piece(piece_id: int, palette: int = 0) -> pygame.Surface`. Both cache, and raise `IndexError` for an unknown id.
- Produces in `sprite_data.py`: `PANE_FRAME_INTACT = 163`, `BRICK_FRAMES = (5, 4)`, `SILL_OBSTACLE_FRAME = 214`, `LIFE_ICON_PIECE = 17`.

- [ ] **Step 1: Implement `tools/decode_exe_tables.py`**
  - Usage: `python3 -I tools/decode_exe_tables.py FixitFelixJr.exe`. Map VA → file offset through the PE section headers.
  - Read 10-byte records `<5h` = `[id, x, y, w, h]` in 8px cells: 216 from `0x418458`, 27 from `0x418348`. Assert `record[0] == index` for every record, and exit non-zero if it fails (that's the alignment check).
  - Write `src/exe_tables.py` with a header comment naming the source addresses and "generated, do not edit".
  - Write the JSON and contact sheets (labelled `#id (x,y) wxh` from `Data/felix0.png`) into `docs/ghidra-output/pass4/`, replacing the misaligned ones.
- [ ] **Step 2: Run it** — `python3 -I tools/decode_exe_tables.py FixitFelixJr.exe`. Expected: no assertion failures; `src/exe_tables.py` has 216 + 27 entries.
- [ ] **Step 3: Add `get_frame` / `get_piece` to `SpriteSheet`**, slicing the palette atlas like `get_sprite` does. Add the named ids to `sprite_data.py`.
- [ ] **Step 4: Write tests** in `tests/test_exe_tables.py`:

```python
def test_pane_frames_span_glass_to_black():
    assert SPRITE_FRAMES[163] == (304, 0, 16, 16)
    assert SPRITE_FRAMES[168] == (320, 0, 16, 16)

def test_floor_pieces_match_floor_heights():
    assert BUILDING_PIECES[10] == (0, 0, 224, 48)
    assert BUILDING_PIECES[11] == (0, 48, 224, 56)
    assert BUILDING_PIECES[12] == (0, 104, 224, 56)
    assert BUILDING_PIECES[13] == (0, 160, 224, 56)
    assert BUILDING_PIECES[9] == (288, 800, 224, 160)

def test_cell_pieces():
    assert BUILDING_PIECES[16] == (272, 0, 24, 48)
    assert BUILDING_PIECES[2] == (320, 48, 48, 64)
    assert BUILDING_PIECES[6] == (224, 48, 48, 40)

def test_get_frame_unknown_id_raises():  # headless SpriteSheet
    with pytest.raises(IndexError):
        SpriteSheet().get_frame(216)
```

- [ ] **Step 5: Run** `python3 -m pytest tests/test_exe_tables.py -v`. Expected: all pass.
- [ ] **Step 6: Checkpoint.** The user reviews the regenerated contact sheets and commits.

### Task 2: Level configuration

**Files:**
- Create: `src/level_config.py`
- Test: `tests/test_level_config.py`

**Interfaces:**
- Produces:
  - `class FloorType(IntEnum)`: `GROUND=0, SECOND=1, BRICK_SHORT=2, BRICK_TALL=3, ROOF=4`
  - `class CellKind(IntEnum)`: `PLAIN=0, DOOR=1, ARCHED=2, PEDIMENT_A=3, PEDIMENT_B=4`
  - `FLOORS_PER_SECTION = 4`, `MAX_CONFIGURED_LEVEL = 10`, `FACADE_X = 8`, `FACADE_WIDTH = 224`, `STREET_Y = 320`
  - `FLOOR_HEIGHT: dict[FloorType, int]`, `FLOOR_PIECE: dict[FloorType, int]` (12, 13, 10, 11, 9), `CELL_PIECE: dict[CellKind, int]` (16, 2, 6, 14, 15)
  - `CENTER_CELL_KIND: dict[FloorType, CellKind]`: GROUND → DOOR, SECOND → ARCHED, BRICK_SHORT → PEDIMENT_A, BRICK_TALL → PEDIMENT_B `[ASSUMED, verify in Task 4]`
  - `COLUMN_X: dict[FloorType, tuple[int, ...]]`: (40, 72, 96, 144, 176) for GROUND/SECOND, (40, 72, 104, 144, 176) for the brick types
  - `@dataclass(frozen=True) class LevelConfig: floor_count, section_count, bird_pairs, sill_obstacles, drop_hazards` (all `int`)
  - `get_level_config(level: int) -> LevelConfig` and `get_floor_sequence(level: int) -> tuple[FloorType, ...]`. Level is 1-based and capped at 10; `level < 1` raises `ValueError`.

- [ ] **Step 1: Implement `src/level_config.py`** with the spec §2 table and sequences, citing `FUN_00409610` / `0x419d78`.
- [ ] **Step 2: Write tests:**

```python
def test_level_table_rows():
    assert get_level_config(1) == LevelConfig(9, 2, 0, 0, 0)
    assert get_level_config(4) == LevelConfig(13, 3, 1, 2, 0)
    assert get_level_config(6) == LevelConfig(17, 4, 2, 4, 1)
    assert get_level_config(9) == LevelConfig(17, 4, 2, 4, 3)

def test_levels_past_ten_use_level_ten():  # Review Focus 4
    assert get_level_config(11) == get_level_config(10)
    assert get_level_config(50) == get_level_config(10)

def test_floor_sequence_matches_floor_count_and_ends_with_roof():
    for level in range(1, 12):
        sequence = get_floor_sequence(level)
        assert len(sequence) == get_level_config(level).floor_count
        assert sequence[0] == FloorType.GROUND and sequence[1] == FloorType.SECOND
        assert sequence[-1] == FloorType.ROOF
        assert len(sequence) - 1 == get_level_config(level).section_count * FLOORS_PER_SECTION

def test_level_zero_raises():
    with pytest.raises(ValueError):
        get_level_config(0)
```

- [ ] **Step 3: Run** `python3 -m pytest tests/test_level_config.py -v`. Expected: all pass.
- [ ] **Step 4: Checkpoint.** The user reviews and commits.

---

## Phase B — Building and camera

### Task 3: Building model and camera

**Files:**
- Create: `src/camera.py`
- Rewrite: `src/entities/building.py` (model half; drawing comes in Task 4)
- Rewrite: `tests/test_building.py` (the old `WindowSlot` tests and the `SECTIONS_PER_LEVEL` NameError go away with the old model)
- Test: `tests/test_camera.py`

**Interfaces:**
- Consumes: Task 2's `level_config` names.
- Produces in `camera.py`, `class Camera`:
  - `scroll_y: float`
  - `snapshot() -> None` (stores the previous scroll for interpolation; called once per tick)
  - `to_screen_y(world_y: float, alpha: float = 1.0) -> int` (screen = world + interpolated scroll)
  - `scroll_toward(target_scroll_y: float, speed: float) -> bool` (moves without overshoot; True once it has arrived)
- Produces in `building.py`:
  - `PANE_INTACT = 0`, `PANE_SMASHED = 5`
  - `class WindowCell`:
    - `kind: CellKind`, `column: int`, `x: int`, `width: int` (from the cell piece), `floor_index: int`
    - pane state: `top_pane: int`, `bottom_pane: int`, `door_damage: int`, `has_sill_obstacle: bool`
    - properties: `is_damageable` (not ARCHED), `is_broken`, `center_x`
    - methods: `damage(is_heavy: bool, rng: random.Random) -> None`, `fix() -> None`
  - `class Floor`: `index`, `floor_type`, `bottom_y`, `height`, `cells: list[WindowCell]` (empty for ROOF), and a `top_y` property
  - `class Building(level: int, rng: random.Random)`:
    - state: `floors`, `section_index`, `section_count`
    - floor and cell lookup: `section_floors(section_index: int | None = None) -> list[Floor]`, `cell(local_row: int, column: int) -> WindowCell` (active section, `local_row` 0 = bottom), `floor_at_y(world_y: float) -> Floor | None`
    - window state: `broken_count` (property: broken cells in the active section), `damage(cell, is_heavy) -> None`, `fix(cell) -> int`
    - section flow: `is_section_clear() -> bool`, `is_last_section` (property), `advance_section() -> None` (raises `RuntimeError` on the last section)
    - geometry: `ledge_y(section_index: int | None = None) -> int` (the top of the section's top floor), `scroll_target(section_index: int) -> int` (the sum of heights of the floors below the section)

- [ ] **Step 1: Implement `camera.py` and the `building.py` model**
  - `fix()` returns 0 for an unbroken cell. Otherwise it fixes the cell, then returns **500** if `broken_count` is now 0, else **100** (`FUN_00409a70`).
  - Light damage sets one random pane to `rng.randint(1, 5)`; heavy damage sets one random pane to 5. For DOOR cells, both set `door_damage` the same way.
  - ARCHED cells ignore `damage`.
  - Floors are laid out upward from `STREET_Y` using `FLOOR_HEIGHT`. Cell x comes from `COLUMN_X`, and the center cell's kind from `CENTER_CELL_KIND`.
- [ ] **Step 2: Write tests** (seeded `random.Random(0)`):

```python
def test_level_one_layout():
    b = Building(1, random.Random(0))
    assert len(b.floors) == 9 and b.section_count == 2
    assert b.floors[0].bottom_y == 320 and b.floors[0].height == 56
    assert b.floors[1].bottom_y == 264
    assert [c.kind for c in b.floors[0].cells][2] == CellKind.DOOR
    assert b.floors[8].cells == []

def test_fix_scores_100_then_500_for_last():
    b = Building(1, random.Random(0))
    first, second = b.cell(0, 0), b.cell(1, 4)
    b.damage(first, is_heavy=True); b.damage(second, is_heavy=False)
    assert b.broken_count == 2
    assert b.fix(first) == 100
    assert b.fix(second) == 500
    assert b.is_section_clear()

def test_fix_intact_window_scores_nothing():
    b = Building(1, random.Random(0))
    assert b.fix(b.cell(0, 0)) == 0

def test_arched_window_ignores_damage():
    b = Building(1, random.Random(0))
    arched = b.cell(1, 2)
    b.damage(arched, is_heavy=True)
    assert not arched.is_broken

def test_broken_count_only_counts_active_section():
    b = Building(1, random.Random(0))
    b.damage(b.section_floors(1)[0].cells[0], is_heavy=True)
    assert b.broken_count == 0

def test_scroll_target_and_ledge():
    b = Building(1, random.Random(0))
    assert b.scroll_target(0) == 0
    assert b.scroll_target(1) == sum(f.height for f in b.floors[:4])
    assert b.ledge_y(0) == b.floors[3].top_y

def test_advance_past_last_section_raises():
    b = Building(1, random.Random(0))
    b.advance_section()
    with pytest.raises(RuntimeError):
        b.advance_section()

def test_camera_scrolls_without_overshoot():
    camera = Camera()
    arrived = [camera.scroll_toward(5, 2) for _ in range(3)]
    assert arrived == [False, False, True] and camera.scroll_y == 5
```

- [ ] **Step 3: Run** `python3 -m pytest tests/test_building.py tests/test_camera.py -v`. Expected: all pass. (Other suites will break against the new model until Tasks 5–8; that's expected.)
- [ ] **Step 4: Checkpoint.** The user reviews and commits.

### Task 4: Building rendering + visual check tool

**Files:**
- Modify: `src/entities/building.py` (add drawing)
- Create: `tools/render_level.py`

**Interfaces:**
- Consumes: Task 1's `get_frame`/`get_piece`, Task 3's model.
- Produces: `Building.draw(screen, sprites: SpriteSheet, camera: Camera, palette: int) -> None`, and `Building.glass_rect(cell) -> pygame.Rect` (world; pane-window glass at `cell.x + 6, floor.top_y + 12, 12×23`, the `FUN_00404ea0` example rect; door glass spans the piece).

- [ ] **Step 1: Implement `Building.draw`**
  - Draw each floor piece bottom-aligned to `floor.bottom_y` at `FACADE_X`. The roof's 160px art is bottom-aligned to its row `[ASSUMED]`.
  - Draw cell pieces at `(cell.x, floor.bottom_y - piece_height)`.
  - Pane windows: draw panes `get_frame(PANE_FRAME_INTACT + state)` at `(cell.x + 4, top + 12)` and `(cell.x + 4, top + 25)`, where `top = floor.bottom_y - piece_height` (top/bottom offsets `0xC` / `0x19` are **[EXE]**; the +4 x-centering is **[ASSUMED]**).
  - Door: piece `2 + min(door_damage, 3)` `[ASSUMED]`.
  - Skip floors fully off screen.
- [ ] **Step 2: Implement `tools/render_level.py`**
  - Usage: `python3 tools/render_level.py --level N --out <dir>`. Headless.
  - Renders the **whole building** at 1× (tall image) twice: all intact, and one with a mix of pane states 0–5 across a floor plus a damaged door.
- [ ] **Step 3: Run it** for levels 1 and 5 into the scratchpad. Expected: PNGs written, no exceptions.
- [ ] **Step 4: USER CHECKPOINT (visual).** The user opens the PNGs and confirms:
  - the floor and cell pieces line up (resolves the spec §2 open items: pediment A/B, roof placement, the 104px center cell);
  - pane states 1–4 read as increasing damage;
  - the door damage order looks right.

  Fix the `[ASSUMED]` constants from the answers, then the user commits.

---

## Phase C — Felix

### Task 5: Felix on the building model

**Files:**
- Rework: `src/entities/felix.py`
- Modify: `src/constants.py`
- Rewrite: `tests/test_felix.py`

**Interfaces:**
- Consumes: `Building.cell`, `WindowCell.center_x`, `Floor.bottom_y`, `Building.fix`, `Camera.to_screen_y`.
- Produces on `Felix`:
  - position: `column: int`, `local_row: int`, `place_at(local_row: int, column: int, building) -> None`, `world_pos(alpha: float = 1.0) -> tuple[float, float]` (center x, feet y), `hitbox() -> pygame.Rect` (world, 12×28 centered on the feet `[ASSUMED]`)
  - status: `is_invulnerable` (property), `last_fixed_points: int` (0 when nothing was fixed this tick)
  - actions: `hit(sound=None) -> bool` (True if it landed), `activate_invulnerability(sound=None) -> None`
  - unchanged: `tick(input_handler, building, sound=None)`, `score`, `lives`, `is_alive`, `add_score`
  - `draw(screen, sprites, camera, palette, alpha=1.0)`
- Constants: `INVULNERABLE_TICKS = 480` (`0x4217a4` timer), `BONUS_LIFE_THRESHOLD = 5000`. Remove `SUPER_DURATION_TICKS`.

- [ ] **Step 1: Rework movement**
  - Anchor = `(cell.center_x, floor.bottom_y)`.
  - LEFT/RIGHT starts a walk that accelerates by `FELIX_HORIZONTAL_ACCEL` (0.5, `[ASSUMED]`) up to 2.0 and stops on the next cell's center. Pressing the opposite direction mid-walk negates the velocity and retargets the cell it came from.
  - UP/DOWN keep the existing jump, targeting `local_row ± 1`. UP is refused when `local_row == 3` or the current cell `has_sill_obstacle`; DOWN is refused at `local_row == 0`.
  - Remove the `is_super` instant repair and the 100 + 500 double award.
- [ ] **Step 2: Rework the hammer**
  - When the strike completes, call `points = building.fix(cell)`.
  - If `points`: `add_score(points)`, play `window_fixed` (500) or `hammer_hit` (100), and set `last_fixed_points`.
- [ ] **Step 3: Rework hits**
  - `hit()` returns False while invulnerable or already stunned. Otherwise it reuses the existing stun flow.
  - The knockback start becomes anchor-relative: `FELIX_STUN_START_BELOW = 160` px below the anchor's feet `[ASSUMED]`. That's the old screen-y 480 minus the 320 screen height, so the drop still starts off screen. `tick()` doesn't need the camera.
  - Use the knocked-down frames from the regenerated contact sheet if they read better than `felix_stunned`. That's optional; note the choice.
- [ ] **Step 4: Write tests** (a `Building(1, Random(0))`, the existing `MockInput` pattern, and a helper that ticks N times):

```python
def test_walk_accelerates_and_stops_on_next_cell():
    # press RIGHT once; speed grows tick by tick, never exceeds 2.0,
    # and Felix ends exactly on building.cell(0, 3).center_x
def test_reverse_mid_walk_returns_to_start_cell(): ...
def test_up_blocked_by_sill_obstacle():
    b.cell(0, 2).has_sill_obstacle = True  # press UP → local_row stays 0
def test_up_blocked_on_top_floor_and_down_on_bottom(): ...
def test_one_swing_fixes_window_and_scores_100(): ...
def test_last_window_scores_500(): ...
def test_swing_at_intact_window_scores_nothing(): ...
def test_bonus_life_every_5000(): ...  # add_score(5000) → lives 11; add_score(4999) → still 11
def test_invulnerable_ignores_hit_and_expires_after_480_ticks(): ...
```

- [ ] **Step 5: Run** `python3 -m pytest tests/test_felix.py -v`. Expected: all pass.
- [ ] **Step 6: Checkpoint.** The user reviews and commits.

---

## Phase D — Ralph, bricks, and the game flow

### Task 6: Ralph state machine

**Files:**
- Rewrite: `src/entities/ralph.py`
- Modify: `src/constants.py`
- Test: `tests/test_ralph.py`

**Interfaces:**
- Consumes: `Building.ledge_y`, `Building.floor_at_y`, `Building.damage`, `Building.section_index`.
- Produces:
  - `class RalphState(Enum)`: `WALK, POUND, SECTION_POSE, CLIMB, RAGE, IDLE`
  - `@dataclass class RalphEvents`: `brick_spawns: list[tuple[float, float]]`, `is_drop_hazard_requested: bool`, `is_climb_finished: bool`
  - `class Ralph(rng: random.Random)`:
    - state: `x`, `y` (world, center x / feet y), `state`
    - placement: `place_on_ledge(building) -> None` (x = 120, y = `ledge_y()`, WALK)
    - actions: `start_rage() -> None`, `start_section_clear() -> None` (SECTION_POSE), `start_climb(building, from_y: float, first_heavy_cell=None) -> None`
    - `tick(building, level: int) -> RalphEvents`
    - `draw(screen, sprites, camera, palette)`
- Constants (`[EXE]` unless noted):
  - patrol: `RALPH_WALK_SPEED = 1.0`, `RALPH_PATROL_CENTER_X = 120`, `RALPH_PATROL_SIDE_X = (72, 169)`
  - pounding: `RALPH_POUND_BASE_TICKS = 9`, `RALPH_POUND_RANDOM_TICKS = 8` (rand 0..7), `RALPH_POUND_DURATION_TICKS = 60` `[ASSUMED]`
  - drop hazard: `RALPH_CYCLES_PER_DROP = 3`, `RALPH_DROP_DELAY_TICKS = 30`
  - climb: `RALPH_CLIMB_SPEED = 1.0`, `RALPH_CLIMB_DAMAGE_INTERVAL_TICKS = 10`, `RALPH_CLIMB_DAMAGE_CHANCE = 0.5`
  - rage: `RALPH_RAGE_WINDUP_TICKS = 80`, `RALPH_RAGE_BRICK_INTERVAL_TICKS = 8`, `RALPH_RAGE_DURATION_TICKS = 240`
  - other: `RALPH_SECTION_POSE_TICKS = 60` `[ASSUMED]`, `BRICK_SPAWN_SPREAD = 32`, `BRICK_SPAWN_DROP = 8`
  - Remove the `RALPH_THROW_*` constants.

- [ ] **Step 1: Implement the state machine**
  - **Patrol:** after arriving at a target, POUND for the pound duration, then pick the next target. Off center → 120; at center → alternate 72 / 169.
  - **Bricks:** while pounding, spawn one at `(x + rng.randint(-32, 31), y + 8)` every `9 + rng.randint(0, 7)` ticks.
  - **Drop hazards:** count completed walk/pound cycles. On every 3rd, start the 30-tick timer, then set `is_drop_hazard_requested`; the caller decides whether the level allows it.
  - **Climb:**
    - Slide to x = 120, then move y up 1 px/tick to `building.ledge_y()`. The caller has already advanced the section.
    - Every 10 ticks, with a 50% roll, `building.damage(random damageable cell on floor_at_y(y), is_heavy=False)` if that floor is in the active section.
    - `first_heavy_cell` gets one heavy hit at climb start (used for the level-start door).
    - Arrival sets `is_climb_finished` and returns to WALK.
  - **Rage:** wind-up, then a brick every 8 ticks for 240 ticks, then WALK.
  - **Drawing:** keep the existing named Ralph sprites; climb uses `ralph_climb`, pound/rage use `ralph_smash`.
- [ ] **Step 2: Write tests** (seeded rng, a `Building(5, …)` so drop hazards apply):

```python
def test_patrol_order_is_center_left_center_right(): ...  # record arrival xs: 72, 120, 169, 120 ...
def test_pound_brick_interval_between_9_and_16_ticks(): ...
def test_brick_spawn_within_spread_of_ralph(): ...  # every spawn x in [x-32, x+31], y == ralph.y + 8
def test_drop_hazard_requested_after_three_cycles(): ...
def test_rage_waits_80_then_brick_every_8_for_240(): ...  # 30 bricks, first at tick 80
def test_climb_reaches_new_ledge_and_damages_section(): ...  # advance_section(); start_climb(b, old_y); tick until finished; broken_count > 0
```

- [ ] **Step 3: Run** `python3 -m pytest tests/test_ralph.py -v`. Expected: all pass.
- [ ] **Step 4: Checkpoint.** The user reviews and commits.

### Task 7: Bricks

**Files:**
- Rewrite: `src/entities/brick.py`
- Modify: `src/constants.py` (remove the `BRICK_FALL_VEL_*` / `BRICK_DRIFT_X_VEL` / `BIRD_*_VEL` misreadings, and `MAX_BRICKS`)
- Test: `tests/test_brick.py`

**Interfaces:**
- Consumes: `RalphEvents.brick_spawns`, `Felix.hitbox/hit/is_invulnerable`, `Building.glass_rect/damage/section_floors`.
- Produces:
  - `class Brick`: `x`, `y`, `is_bouncing`, `is_active`, `rect() -> pygame.Rect`
  - `class BrickField(rng: random.Random)`:
    - `spawn(x: float, y: float) -> None` (ignored past 64 live bricks)
    - `tick(building, felix, level: int, sound=None) -> bool` (True if Felix was hit this tick)
    - `clear() -> None`, `reset_break_budget() -> None`
    - `draw(screen, sprites, camera, palette, alpha)`
- Constants `[EXE]`:
  - fall: `BRICK_FALL_SPEED = 1.9`, `BRICK_MAX_LIVE = 64`, `GROUND_Y = 317`
  - window breaks: `BRICK_WINDOW_BREAK_ODDS = 200`, `BRICK_WINDOW_BREAK_MIN_LEVEL = 2`, `BRICK_WINDOW_BREAKS_PER_SECTION = 4` (the reset point is `[ASSUMED]`)
  - bounce: `BRICK_BOUNCE_VX = 1.3`, `BRICK_BOUNCE_VY = -3.0`, `BRICK_BOUNCE_GRAVITY = 0.4`, `BRICK_BOUNCE_TICKS = 40` `[ASSUMED]`

- [ ] **Step 1: Implement**
  - **Falling:** straight down at 1.9.
  - **Felix:** if the rect overlaps Felix's hitbox and Felix is invulnerable, start a bounce (vx = ±1.3 by coin flip, vy = −3.0); otherwise `felix.hit()`, the brick vanishes, and return True.
  - **Windows:** at level ≥ 2 with budget left, if it overlaps an **intact** active-section cell's `glass_rect` and `rng.randrange(200) == 99`, light-damage that cell, use one budget, and the brick vanishes.
  - **Ground:** at y ≥ 317, bounce.
  - **Bounces:** apply gravity, blink, and deactivate after the bounce ticks.
  - **Drawing:** frame 5 with frame 4 stacked directly above it `[ASSUMED]`.
- [ ] **Step 2: Write tests:**

```python
def test_brick_falls_1_9_per_tick(): ...
def test_brick_hits_felix_once_and_vanishes(): ...
def test_invulnerable_felix_bounces_brick_and_keeps_lives(): ...
def test_level_one_bricks_never_break_windows(): ...  # 10_000 overlapping ticks, rng seeded
def test_window_break_budget_caps_at_four_per_section(): ...  # rng stub returning 99 always
def test_only_intact_windows_can_be_broken_by_bricks(): ...
def test_ground_bounce_then_disappears(): ...
```

- [ ] **Step 3: Run** `python3 -m pytest tests/test_brick.py -v`. Expected: all pass.
- [ ] **Step 4: Checkpoint.** The user reviews and commits.

### Task 8: Game phases, GameScene, HUD

**Files:**
- Create: `src/scenes/game_phases.py`
- Rewrite: `src/scenes/game_scene.py`
- Delete: `src/scenes/level_clear_scene.py`
- Modify: `src/constants.py` (remove the timer constants that are now unused)
- Rewrite: `tests/test_game_pause.py`
- Test: `tests/test_game_flow.py`

**Interfaces:**
- Consumes: everything from Tasks 3–7.
- Produces:
  - `class GamePhase`: `tick(game: GameScene) -> GamePhase | None` (a new phase replaces the current one) and `draw_overlay(game, screen) -> None`
  - `LevelStartPhase`:
    - Ralph `start_climb(building, STREET_Y, first_heavy_cell=building.cell(0, 2))`, the door (`[ASSUMED]`, spec §5).
    - Then wait `READY_PAUSE_TICKS = 180` (`FUN_004086e0`) showing `LEVEL N`.
    - Then go to `PlayPhase`.
  - `PlayPhase` order per tick: Felix, Ralph, bricks; this task stubs Nicelanders and hazards as no-ops. Then:
    - on Felix hit with no lives left → `game.end_game()`;
    - on `is_section_clear()` → `SectionClearPhase`.
  - `SectionClearPhase`:
    - bricks cleared; budget reset; Ralph `start_section_clear()`; "YOU FIXED IT!" shown;
    - if it was the last section → `LevelEndPhase`;
    - else `building.advance_section()`, Ralph `start_climb(building, ralph.y)`, then `camera.scroll_toward(building.scroll_target(new), 2.0)` each tick (`FUN_00408810`);
    - when the camera arrives: `felix.place_at(0, felix.column, building)` → `PlayPhase`.
  - `LevelEndPhase`: Task 11 fills it in. For now: a short hold → `game.start_level(level + 1)` → `LevelStartPhase`.
  - `GameScene`:
    - state: `level`, `rng`, `building`, `camera`, `felix`, `ralph`, `bricks`, `phase`
    - flow: `start_level(level: int) -> None` (keeps Felix's score and lives), `end_game() -> None` (idempotent)
    - unchanged: pause handling
- **HUD** in the 24px top band: score `%06d` left, `LEVEL n`, and up to 5 life icons (piece 17) plus `xN` when lives > 5. All `[ASSUMED]` layout.

- [ ] **Step 1: Implement the phases and the slimmed `GameScene`**
  - Drawing order: building, pie/Nicelanders, bricks, hazards, Ralph, Felix, HUD, phase overlay, pause overlay.
  - `camera.snapshot()` once per unpaused tick.
  - Remove the `LevelClearScene` import and file.
  - `end_game()` sets a flag so the game-over transition happens once.
- [ ] **Step 2: Write tests** (headless, seeded rng, scripted `MockInput`):

```python
def test_level_start_damages_section_zero_then_plays(): ...  # tick until PlayPhase; broken_count > 0; door damaged
def test_fixing_all_windows_clears_section_scrolls_and_resumes(): ...
    # fix every broken cell via building.fix; tick; phase is SectionClearPhase;
    # tick until PlayPhase; camera.scroll_y == building.scroll_target(1); felix.local_row == 0
def test_last_section_goes_to_level_end_then_next_level_keeps_lives_and_score(): ...
def test_no_hits_or_scoring_outside_play_phase(): ...  # Review Focus 1: brick placed on Felix during SectionClearPhase → lives unchanged
def test_game_over_fires_once(): ...                   # Review Focus 3: lives=1, two bricks on Felix same tick → one replace() call
def test_pause_freezes_scroll_and_climb(): ...         # Review Focus 5
```

- [ ] **Step 3: Run** `python3 -m pytest tests/ -v`. Expected: all pass.
- [ ] **Step 4: Launch smoke** — `timeout 5 python3 src/main.py`. Expected: exits on timeout with no traceback. This is not visual verification; the user plays.
- [ ] **Step 5: USER CHECKPOINT (playtest).** The user plays level 1 through both sections and checks:
  - Ralph climbs in and wrecks windows;
  - walk acceleration feels right;
  - one swing fixes a window;
  - bricks fall from Ralph's pounding;
  - the section clear scrolls up.

  Tune the `[ASSUMED]` constants from the feedback, then the user commits.

---

## Phase E — Nicelanders and pies

### Task 9: Nicelanders, pies, rage

**Files:**
- Create: `src/entities/nicelander.py`
- Rewrite: `src/entities/pie.py`
- Modify: `src/scenes/game_phases.py` (PlayPhase and SectionClearPhase hooks), `src/sprite_data.py` (Nicelander frame ids)
- Test: `tests/test_nicelander.py`

**Interfaces:**
- Consumes: `Building`, `Felix.local_row/column/activate_invulnerability`, `Ralph.start_rage`.
- Produces:
  - `class Pie(cell: WindowCell)`: `cell`, `is_collected_by(felix, building) -> bool`, `draw(…)`
  - `class Nicelander(cell, character: int)`: `cell`, `pie: Pie | None`, `tick() -> None` (rise animation; creates the pie at the handoff frame), `draw(…)`
  - `class NicelanderDirector(rng: random.Random)`:
    - `tick(building, felix) -> bool` (True when the pie was collected this tick)
    - `on_window_fixed(cell) -> None`, `clear() -> None`, `draw(…)`
- Constants `[EXE]`: `NICELANDER_SPAWN_TICKS = 1500`, `NICELANDER_REARM_TICKS = 600`, `NICELANDER_MIN_BROKEN = 5`, `NICELANDER_MAX_CANDIDATES = 3`, `NICELANDER_CHARACTERS = 6`. Rise/handoff frame holds `[ASSUMED]`.
- Frame ids: pick from the regenerated contact sheet (peeks, busts and the handoff, roughly 129–154 in code ids) and record them in `sprite_data.py` with a comment per group.

- [ ] **Step 1: Implement**
  - **Timer:** at 0 → try to spawn. With `broken_count >= 5` and a candidate (bottom pane 5, not Felix's floor, not DOOR/ARCHED), pick one of up to 3 and set 1500; with fewer than 5 broken, set 600. It counts down only while no Nicelander is out.
  - **Collecting:** Felix on the pie's cell → hide the pie and Nicelander, `felix.activate_invulnerability()`, `ralph.start_rage()`, play `pie_pickup`.
  - **Fixing the window:** `on_window_fixed(cell)` removes a Nicelander/pie on that cell. PlayPhase calls it when `felix.last_fixed_points` is non-zero. SectionClearPhase calls `clear()`.
- [ ] **Step 2: Write tests:**

```python
def test_no_nicelander_with_fewer_than_five_broken(): ...
def test_nicelander_only_in_smashed_bottom_pane_off_felix_floor(): ...
def test_pie_appears_at_handoff_and_collect_grants_480_and_rage(): ...
def test_fixing_the_window_removes_nicelander_and_pie(): ...  # Review Focus 2
def test_section_clear_removes_nicelander_and_pie(): ...       # Review Focus 2
def test_timer_rearms_to_600_when_too_few_broken(): ...
```

- [ ] **Step 3: Run** `python3 -m pytest tests/ -v`. Expected: all pass.
- [ ] **Step 4: Checkpoint.** The user reviews and commits.

---

## Phase F — Hazards

### Task 10: Sill obstacles, birds, drop-hazards

**Files:**
- Create: `src/entities/hazards.py`
- Delete: `src/entities/bird.py`
- Modify: `src/scenes/game_phases.py`, `src/constants.py` (remove the old `BIRD_*` / `PIE_*` interval constants)
- Test: `tests/test_hazards.py`

**Interfaces:**
- Consumes: `LevelConfig`, `Building.section_floors/cell`, `RalphEvents.is_drop_hazard_requested`, `Felix.hitbox/hit`.
- Produces:
  - `place_sill_obstacles(building, count: int, rng) -> None`: sets `has_sill_obstacle` on random cells of the section's top 3 floors, at most 2 per floor, never ARCHED (`FUN_00406e00`).
  - `class Bird(floor, is_from_right: bool)`
  - `class DropHazard(x: float, start_y: float, target_cell)`
  - `class HazardField(rng)`:
    - `start_section(building, config: LevelConfig) -> None` (places obstacles and birds)
    - `request_drop(ralph, building, config) -> None`
    - `tick(building, felix) -> bool` (True if Felix was hit)
    - `clear() -> None`, `draw(…)`
- Constants `[EXE]`:
  - birds: `BIRD_SPEED = 0.5`, `BIRD_WRAP_LEFT_X = -32`, `BIRD_WRAP_RIGHT_X = 272`
  - drop hazards: `DROP_HAZARD_FALL_SPEED = 1.9`, `DROP_HAZARD_MAX_LIVE = 3`, `DROP_HAZARD_BLINKS = 4`
- Drop-hazard sprite is **[OPEN]**. Use `SILL_OBSTACLE_FRAME` with a `# TODO: drop-hazard sprite unidentified (spec §8)` comment, and say so at the checkpoint.

- [ ] **Step 1: Implement**
  - **Activation:** entering `PlayPhase` from `LevelStartPhase` or `SectionClearPhase` calls `start_section`. SectionClearPhase calls `clear()` and removes the obstacle flags of the old section.
  - **Drop hazards:** honored only while live < `config.drop_hazards` and < 3. The target is the column nearest Ralph's x and a random floor of the section. It falls to that cell's sill and stays; touching it hits Felix, then it blinks 4 times and vanishes.
  - **Drawing:** birds use frames 0–3 (two per direction, from the regenerated sheet).
- [ ] **Step 2: Write tests:**

```python
def test_sill_obstacles_top_three_floors_max_two_per_floor_never_arched(): ...  # many seeds
def test_no_hazards_before_their_levels(): ...  # level 2: no obstacles/birds/drops; level 3: obstacles only
def test_bird_moves_half_pixel_and_wraps(): ...
def test_bird_hits_felix_unless_invulnerable(): ...
def test_drop_hazard_lands_on_sill_and_hits_felix_once(): ...
def test_drop_hazards_capped_by_level_and_three(): ...
```

- [ ] **Step 3: Run** `python3 -m pytest tests/ -v`. Expected: all pass.
- [ ] **Step 4: Checkpoint.** The user plays levels 3–5 (a temporary start-level override is fine; don't leave it in). Then the user commits.

---

## Phase G — Ending and cleanup

### Task 11: Roof sequence, high-score defaults, docs

**Files:**
- Modify: `src/scenes/game_phases.py` (`LevelEndPhase`), `src/scenes/high_score_scene.py`, `src/sprite_data.py` (medal frame ids)
- Modify: `STATUS.md`, `README.md` (gameplay section)
- Test: `tests/test_game_flow.py` (extend), `tests/test_high_scores.py`

**Interfaces:**
- Consumes: `GameScene.start_level`, Ralph's `ralph_fall` sprite, the medal frames.
- Produces:
  - `LevelEndPhase` script `[ASSUMED]` (spec §9), each step a named tick constant:
    1. hold;
    2. medal descends to above Felix (tier by level, as in the old `LevelClearScene`);
    3. Ralph is thrown off the roof (`ralph_fall`, falls off screen);
    4. "YOU FIXED IT!";
    5. `start_level(level + 1)`.
  - `DEFAULT_HIGH_SCORES = [15000, 10000, 8000, 6000, 4000]` (`FUN_0040a060`), blank initials `[ASSUMED]`, used when `scores.dat` is missing.

- [ ] **Step 1: Implement the roof sequence and the high-score defaults.**
- [ ] **Step 2: Remove dead code:** any `sprite_data` entries and constants no longer referenced (`window_*`, `wall_brick`, `niceland_sign`, `shutter_*`, `ledge`, `SKY_BLUE`, `SECTION_CLEAR_TICKS`, `LEVEL_CLEAR_*`). Check with `grep -rn <name> src tests`.
- [ ] **Step 3: Write tests:**

```python
def test_level_end_runs_script_then_next_level_starts(): ...
def test_default_high_scores_when_no_file(tmp_path, monkeypatch): ...  # point SCORES_FILE at tmp_path
```

- [ ] **Step 4: Run** `python3 -m pytest tests/ -v`. Expected: all pass.
- [ ] **Step 5: Update `STATUS.md` and `README.md`** to describe the rebuilt game, and list the remaining `[ASSUMED]`/`[OPEN]` items as tuning knobs.
- [ ] **Step 6: USER CHECKPOINT.** The user plays a full level 1 → 2 transition and commits.

---

## Phase H — Pre-refactor safety net

### Task 12: Test coverage for infrastructure, public-API-only tests, coverage tool

Added 2026-10-21 at the user's request. The user plans a refactor after this branch, and this task is the regression net for it. Behavior must not change in this task; it's tests and tooling only. If a test exposes a bug, leave a `# TODO:` comment, mark the test `xfail` with the reason, and report it.

**Files:**
- Create: `requirements-dev.txt` (`coverage==<exact installed version>`; dev-only, the game doesn't need it at runtime), `.coveragerc`
- Create: `tests/test_input_handler.py`, `tests/test_scene_manager.py`, `tests/test_font_renderer.py`, `tests/test_sprite_sheet.py`
- Modify: `tests/test_high_scores.py` (from Task 11; extend it), `tests/test_felix.py`, `tests/test_game_pause.py`, `tests/test_ralph.py`, `tests/test_brick.py`, `tests/test_game_flow.py`
- Modify (only if needed to remove a test's reach into private state): add a read-only public property to the class under test. No behavior changes.
- Modify: `STATUS.md` (a "Running tests" section)

**Interfaces:**
- Consumes: `InputHandler.poll(events)`, `consume_just_pressed()`, `is_pressed`, `is_just_pressed`, `has_lost_focus`; `SceneManager.push/replace/pop/tick/draw/current`, `Scene.on_enter/on_exit`; `FontRenderer.render_text`, `scale_text_to_fit(surface, max_width, preferred_scale)`; `SpriteSheet.get_frame/get_piece/get_sprite`; `high_score_scene.load_scores/save_scores/SCORES_FILE/MAX_SCORES`.
- Produces: a coverage command in `STATUS.md`, and a `.coveragerc` that fails under the threshold.

- [ ] **Step 1: Install the tool.** Run `python3 -m pip install coverage`, then pin the exact installed version in `requirements-dev.txt`.
- [ ] **Step 2: Configure `.coveragerc`.**
  - `[run]`: `source = src`, `branch = True`.
  - Omit the GUI-only modules the user verifies by hand: `src/main.py`, `src/scenes/title_scene.py`, `src/scenes/cutscene_scene.py`, `src/scenes/game_over_scene.py`.
  - `[report]`: `fail_under = 90` `[ASSUMED]` (logic-layer line+branch), `show_missing = True`.
- [ ] **Step 3: Measure first.** Run `python3 -m coverage run -m pytest tests -q && python3 -m coverage report`. Save the before-numbers in the report, per module.
- [ ] **Step 4: Write the infrastructure tests.** Each guards a bug that already shipped once, or a fail-fast rule:

```python
# tests/test_input_handler.py — guards the arrow-key bug (presses lost between render polls and game ticks)
def test_just_pressed_latches_across_polls_until_consumed(): ...   # KEYDOWN in poll 1, empty poll 2, still just-pressed; gone after consume_just_pressed()
def test_held_key_is_pressed_but_not_just_pressed_after_consume(): ...
def test_keyup_clears_pressed(): ...
def test_every_keyboard_map_entry_maps_to_an_action(): ...
def test_focus_loss_reported(): ...                                # whichever event poll() treats as focus loss

# tests/test_scene_manager.py
def test_push_calls_on_enter_and_becomes_current(): ...
def test_replace_calls_on_exit_then_on_enter(): ...
def test_pop_returns_to_previous_scene(): ...
def test_tick_and_draw_go_to_current_scene_only(): ...            # draw receives alpha

# tests/test_font_renderer.py
def test_digit_one_renders_one_not_slash(): ...                    # guards the duplicate-"1" char map bug: "1" and "/" surfaces differ
def test_every_supported_char_renders_nonempty(): ...
def test_scale_text_to_fit_never_exceeds_max_width(): ...          # e.g. "HEY. YOU MOVED MY STUMP!" at 2x into 240
def test_scale_text_to_fit_keeps_preferred_scale_when_it_fits(): ...

# tests/test_sprite_sheet.py — fail-fast rule
def test_get_frame_unknown_id_raises(): ...
def test_get_piece_unknown_id_raises(): ...
def test_flipped_frame_is_mirror_of_unflipped(): ...
def test_every_named_frame_id_in_sprite_data_resolves(): ...       # walk the *_FRAMES tuples and frame-id constants

# tests/test_high_scores.py (extend Task 11's)
def test_save_then_load_round_trips(tmp_path, monkeypatch): ...
def test_scores_capped_at_max_and_sorted_descending(tmp_path, monkeypatch): ...
def test_corrupt_scores_file_behavior(tmp_path, monkeypatch): ...  # pin whatever it does today; if it silently swallows, xfail + TODO (fail-fast rule)
```

- [ ] **Step 5: Use only the public interface.**
  - Remove test reads of private state: `felix._hit_frame_id`, `game._is_paused`, `ralph._target_x`, and `bricks._bricks` / `game.bricks._bricks`.
  - Assert on public behavior instead (position, state, `is_paused`, a `bricks` iterable or count property).
  - Add a read-only property to the class only where no public observable exists. Each one is listed in the report.
  - A MockInput's own private fields are fine.
- [ ] **Step 6: Close the gaps.** Rerun coverage. For each module under 90%, add tests for its uncovered logic branches until the total passes `fail_under`. If a branch can't reasonably be tested (pygame display or audio only), add `# pragma: no cover` with a one-line why. List each one in the report.
- [ ] **Step 7: Run** `python3 -m coverage run -m pytest tests -q && python3 -m coverage report`. Expected: all tests pass, no warnings in the output, and the report passes `fail_under`. Save the after-numbers in the report, per module.
- [ ] **Step 8: Update `STATUS.md`** with how to run the tests and coverage (`pip install -r requirements-dev.txt`, then the Step 7 command).

---

## Out of scope (tracked, not planned)

- Intro story cutscene (stump, bulldozers), attract mode, arcade front-end screens.
- Clouds, fire escapes, street furniture.
- The four per-cell floats and "JUMP OVER".
- Sound-mapping verification (user, by ear).
