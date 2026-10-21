# Ghidra Pass 4 — Findings

_2026-10-19. Full decompilation dump: `docs/ghidra-output/pass4_full.txt` (449 functions, including 74 pointer-only callbacks forced into functions). Script: `tools/GhidraPass4FullDump.java`. Decoded tables and contact sheets: `docs/ghidra-output/pass4/`._

Every value here is **[EXE]**, read from decompiled code or raw `.data` bytes, unless marked otherwise. Times assume 60 ticks/sec.

## Corrections to earlier passes

| Earlier claim | Reality | Evidence |
|---|---|---|
| "Ralph Y = 0x5A (90)" | 0x5A is a **z-order (depth)**. Sprite node layout: x `+0xC`, y `+0xE`, z `+0x10`, frame `+0x12`, flags `+0x1A` (bit0 visible, bit2 flip-H). | `FUN_00402780`, `FUN_0040b3c0` |
| "Section = 6–7 window rows" | A "section" is **one floor strip**. Its "rows" are its **height in 8px units** (6 → 48px, 7 → 56px), matching facade strips B10–B12. Each floor holds **5 column cells** (stride 0x8C). | `FUN_00405e50`, `FUN_00405ca0` |
| "Brick fall velocities -1.8/-2.2/-1.7/-1.5, drift 1.7" | These belong to **window-cell setup** (`FUN_00404ea0`), not bricks: four per-cell floats whose meaning is still unknown. | `FUN_00404ea0` |
| "Bird velocity X=2.2, Y=-4.0" | Same: window-cell type 1 setup values. | `FUN_00404ea0` case 1 |
| "240×320 may be wrong" (mechanics spec §11) | **240×320 is correct.** `gluOrtho2D` over 0xF0 × 0x140, blended with a cabinet rotation setting. Sprites use world y offset by a **vertical scroll** `DAT_0041a248`. | `FUN_00411c40` |

## Rendering

- **Sprite frame table** at `0x418460`, **218 entries** × 10 bytes: `[height, next, x, y, width]` in **8px cells** into the 1024² atlas.
  - Decoded: `pass4/frame_table.json`.
  - Visual index: `pass4/frames_*.png`.
- **Building / UI piece table** at `0x418350`, **27 entries**, same format.
  - Decoded: `pass4/building_table.json`, `building_table.png`.
  - Drawn per floor in 8px rows (`FUN_0040ef90` / `FUN_0040f0a0`).
- Depth-sorted display list (`FUN_0040b3c0`). Sprites clip under a 24px top band (`y < 0x18`), which is likely HUD space.
- Animation defs point to frame lists of 10-byte entries `[frame, flipped_frame, ?, ?, y_offset]`.

### Key frames (sprite table)

- #0–2 birds
- **#3, #4 falling brick (16×16 + 16×8)**
- #5 and #201 clouds
- #6–35 Felix facing right:
  - walk, jump, hammer, strike;
  - **eating pie (#16–23)**;
  - **wearing medal (#24–29)**.
- #36–64 Felix facing left (mirror set)
- **#65–73 Felix knocked down / tumbling**
- #74–127 Ralph:
  - climb, pound and throw variants;
  - **thrown off the roof**;
  - **stump/intro sequence #112–124**.
- **#128–139 Nicelander head peeks (16×16)**
- **#140–151 Nicelander busts (16×24)**
- **#152–153 pie handoff**
- #155–156 pies
- **#162–173 window pane states (16×16)**
- #174–176 "100"/"500" score popups
- #177–179 window-opening pieces
- #180–185 medals
- #186–193 bulldozers and cranes (intro)
- #194–197 dust clouds
- #198/#209/#211 speech bubbles
- #199–200 NICELAND door (closed/open)
- **#214 brick rubble pile**. Our `brick_falling` currently uses this, which is the wrong frame.
- #216–217 facade strips

### Key building pieces

- B0 obstacle/small items cell
- B1 NICELAND sign
- **B2–B4 NICELAND door, three damage states**
- **B5–B6 arched balcony window (intact/damaged)**
- B7 title logo
- **B8 roof cornice**
- **B9 full facade**
- **B10 brick floor strip (224×48)**
- **B11–B12 stone floor strips (224×56)**
- **B13 large-pediment window, B14 small-pediment window, B15 plain window (24×48, two pane holes)**
- **B16 Felix-head life icon**
- B17–B26 front-end text: copyright, HIGH SCORE, 1UP, PRESS START, GAME OVER, CREDITS

## Level start sequence (`FUN_00401470`, three phases)

1. **Wreck climb:** every 31 ticks (about 0.5s) it moves up one floor and calls `FUN_00409eb0`, which turns on the pane sprites for every window of that floor (window types 0, 3, 4). It also repositions 4 sprites across the floor at x = 46/94/142/190. This runs for **6 floors**. It's consistent with Ralph wrecking his way up; what a visible pane looks like still needs confirming.
2. **Street scene:** 4 vehicles drive along y=319, and 5 Nicelanders move 22px apart, bobbing via a 6-entry table at `0x419e8c`.
3. Waits 100 ticks, then **gameplay state**.

## Windows (`FUN_00404ea0` setup, `FUN_00409840` damage, `FUN_00409a70` fixed)

- Each cell stores a type, a glass rect (e.g. `x+6, y+12, 12×23`), sill bounds for Felix, and **two pane sprites**: top at `y+0xC`, bottom at `y+0x19`.
- **Pane state 0–5:** 0 = intact, 5 = smashed. The state is used directly as the pane sprite's frame.
- **Damage `FUN_00409840(heavy, count)`:**
  - **light:** one random pane is set to `rand()%5+1`;
  - **heavy:** a pane is set to 5.
  - Increments the per-player broken-window counter when an intact window is first damaged.
- **Window fixed `FUN_00409a70`:** decrements the counter and awards **500 if it was the last broken window, otherwise 100**. This confirms the "FIX LAST WINDOW 500 PTS" reading.

## Bricks (`FUN_0040d490` update, `FUN_0040d3e0` spawn) — answers the window question

- **64 brick slots.**
- **Spawn:** `x = Ralph.x + rand(-32..+31)`, `y = Ralph.y + 8`. Spawned from Ralph's pound states (`FUN_0040d970` / `FUN_0040dd90`).
- **Falling:** `y += 1.9` px/tick (about 114 px/s), constant speed, straight down with no drift.
- **Hits Felix** (`FUN_0040d230`, a box around Felix's position):
  - normal Felix: the brick vanishes and Felix gets hit (`FUN_0040ca00`);
  - invulnerable (flag at `0x4217a4`, probably Super Felix): the brick **bounces off**.
- **Breaks windows: YES**, under these conditions:
  - only from **level 2 on** (level index > 0);
  - at most **4 window breaks** per counter period (`0x42173c`, reset elsewhere);
  - the brick must overlap an **intact** window's glass on one of 4 floors × 5 columns;
  - even then, only a **1-in-200 chance per tick** (`rand()%200 == 99`).

  When it fires, the brick vanishes and the window takes **light damage**. So on level 1, bricks never break windows.
- **Hits the ground** (y ≥ 317): it bounces out with `vx = ±1.3` (50/50), `vy = -3.0` and gravity 0.4/tick, blinks, then disappears.

## Front end

- Default high-score table: **15000, 10000, 8000, 6000, 4000** (`FUN_0040a060`).

## Sprite table correction

The frame lists start at `0x418cd4`, which overlaps entry 216. So the sprite table really has about **216 entries (0–215)**, and **#216 / #217 in the contact sheets are not real sprites** (they're frame-list bytes read as rects).

## Animations

- Animation defs are 12 bytes: `[u16 id, u16 frame_count][i32 loop_mode][ptr frame_list]`.
- Frame entries are 10 bytes: `[frame, flipped_frame, ?, ?, anchor_y]`. `anchor_y` is the sprite height − 1, so sprites are bottom-anchored.
- `FUN_0040ec50` picks the animation by index from register SI.

Key animations:

| Anim | Frames | What it is |
|---|---|---|
| #0 | 0–1 | birds |
| #2/#3/#4 | — | Felix poses |
| #20–29 | — | Ralph: stand, walk, pound (#24 = 80–85 looped), climb |
| **#66** | **163–168** | **window panes**: `MOV ESI,0x42` at every pane creation |
| #67 | 169–174 | second pane set |
| #68 | 176, 175 | the per-window "500"/"100" score popup |
| #91 | 214 | **sill obstacle** |

The exact pane-state → frame mapping is **[OPEN]**; confirm it visually when building. Art: #163–167 are shards on black, increasingly broken; #168 is full glass.

## Ralph (state machine, table at `0x40e1a4`)

| State | Function | Behavior |
|---|---|---|
| 0 | `FUN_0040df6f` → walk `FUN_0040d870` | Walk at **1 px/tick** to a target x. Not at center → go to **120**. At center → alternate **72** and **169**. So he patrols 120 → 72 → 120 → 169 → … |
| 1 | `FUN_0040e020` → pound `FUN_0040d970` | Pound animation. **One brick every 9 + rand(0..7) ticks** while pounding. Pound sound on frames 0x52/0x54. After **every 3 walk/pound cycles**, a 30-tick timer then calls `FUN_00409360`, which drops a hazard (levels 5+). |
| 3 | `FUN_0040e090` | Special pose on section clear (anim index 0x14 or 0x1a) |
| 4 | `FUN_0040e0e1` → climb `FUN_0040dbb0` | Section climb: slide to x=120, climb **1 px/tick**. **Every 10 ticks, 50% chance of light window damage**, so Ralph wrecks windows as he climbs. Then he takes the new top floor. |
| 6 | `FUN_0040e116` | Idle pose |
| 7 | `FUN_0040e151` → **rage** `FUN_0040dd90` | Wait 80 ticks, then **a brick every 8 ticks for 240 ticks (4s)**, then walk. **Triggered when Felix eats the pie.** |

## Pie / Super Felix / Nicelanders (`FUN_004084c0` gameplay tick, `FUN_00407190`)

- A **Nicelander appears only in a window whose bottom pane is fully smashed** (state 5), never on Felix's floor and never in the door or arched window. It picks randomly from up to 3 candidates, using one of **6 characters** (table `0x419e50`).
- The **pie appears** when the Nicelander's animation reaches frame 2 (the handoff).
- **Timer:**
  - when it's 0, try to spawn a Nicelander, which sets it to 1500 ticks (25s);
  - while no Nicelander is out, it counts down;
  - at 0 with **fewer than 5 broken windows**, it re-arms to 600 ticks (10s).

  So pies only come while **5 or more windows are broken**.
- **Collecting** (Felix's window = pie window): the pie and Nicelander are hidden, Felix is **invulnerable for 480 ticks (8s)** (flag `0x4217a4`; bricks bounce off), and **Ralph goes into rage**.

## Level structure (`FUN_00409610`, config table `0x419d78`, 5 ints/level, capped at level 10)

| Levels | Floors | Sections | Birds/section | Sill obstacles/section | Ralph drop-hazards |
|---|---|---|---|---|---|
| 1–2 | 9 | 2 | 0 | 0 | 0 |
| 3 | 13 | 3 | 0 | 2 | 0 |
| 4 | 13 | 3 | 1 pair | 2 | 0 |
| 5 | 17 | 4 | 1 pair | 3 | 1 |
| 6 | 17 | 4 | 2 pairs | 4 | 1 |
| 7–8 | 17 | 4 | 2 pairs | 4 | 2 |
| 9–10 | 17 | 4 | 2 pairs | 4 | 3 |

- **Floor-type sequence, bottom to top:**
  - levels 1–2: `0,1,2,3,2,3,2,2,4`;
  - levels 3–4: `0,1,(2,3)×4,2,2,4`;
  - levels 5+: `0,1,(2,3)×6,2,2,4`.
- **Floor types:**
  - **0 = ground** (stone, 56px), door in the center column;
  - **1 = second floor** (56px), arched balcony window in the center;
  - **2/3 = brick floors** (48 / 56px), pediment window in the center column;
  - **4 = roof**.
- **Window x positions** (8px tiles × 8):
  - floors 0–1: **40, 72, 96 (wide), 144, 176**;
  - floors 2–3: **40, 72, 104, 144, 176**.
- Floor background is drawn at **x=8, 224 wide** (centered in 240). Floors stack upward from y=320.
- **A section is 4 floors.** Floors 0–3 are the first active set, and Ralph starts on top of floor 4 at x=120.
- Building-piece indices per floor/cell: floors 0–4 → 12, 13, 10, 11, 9; cells 0–4 → 16, 2, 6, 14, 15. **Some appear off by one** against my parse of the `0x418350` table (roof → 9, plain window → 16). **[OPEN]**: verify by assembling a level image from the data.

## Birds (`FUN_004067d0` placement, `FUN_00406bb0` update)

- Pairs per section: one enters from x=272 (flipped), one from x=−32, each on a different random floor among the section's top 3.
- They move **0.5 px/tick** (1px every other tick) and wrap from −32 to 272.
- **Contact hurts Felix** unless invulnerable.
- Only active in the current section; cleared on section clear.

## Sill obstacles (`FUN_00406e00`)

- Count per section comes from the level table (from level 3).
- Placed on a random floor among the section's top 3, **at most 2 per floor**, in a random column whose cell isn't type 2 (arched).
- Sits at the **sill center, y = sill + 9**, using anim #91 (frame 214). It's attached to the cell (`cell+0x2C`).
- **Blocks Felix's jump UP from that window** (`FUN_0040b5e0`: up only if `cell+0x2C == 0`). This is the "BLOCK YOUR PATH" rule.

## Ralph drop-hazards (`FUN_00409360` spawn, `FUN_004073f0` update; levels 5+)

- Up to the level's limit (1–3), max 3 at once.
- Spawned at Ralph's y + 8, aimed at a column chosen by Ralph's position and a random floor (0–3) of the section.
- **Falls 1.9 px/tick to that window's sill and stays there.**
- **Touching it hits Felix**; it then blinks 4 times and disappears.
- Its sprite/animation is **[OPEN]** (it's created in init code via register-passed ids).

## Felix movement (`FUN_0040b5e0` idle, `FUN_0040b9f0` walk)

- Input bits: `0x40` hammer, `0x2` up, `0x1` down, plus edge-triggered left/right flags.
- **Walk:** velocity accelerates by `_DAT_00416b80` per tick up to **±2.0**. Reversing the held direction flips velocity. Felix **stops when he reaches a window** (`FUN_0040b4c0`) or a floor bound, so it's effectively one window per press with acceleration.
- **Up** is blocked by a sill obstacle on the current window and at the top active floor.
- **Hammer complete** (`FUN_0040bc80`): window-fixed scoring (`FUN_00409a70`). **When the broken count reaches 0 → section clear**: bricks cleared, Ralph section pose, section's birds removed.

## Section clear → scroll (`FUN_00408810`)

1. Wait until Ralph's climb state finishes.
2. **Scroll the camera up 2 px/tick (120 px/s)** until it reaches the target (sum of the new floors' heights).
3. Felix moves up.
4. When Felix is idle, the next section activates (Nicelander reset, etc.).

After the last section, `FUN_004089b0` increments the level and resets the scroll and counters. `FUN_004086e0` adds a **180-tick (3s)** pause before play starts.

## Table alignment correction (2026-10-21)

The pass-4 decoder read both tables **one field late**. The code indexes them from `0x418458` (sprites) and `0x418348` (building pieces), not `0x418460` / `0x418350` (`LEA EAX,[EAX*0x2 + 0x418458]` at `0040ee4f`, `[EAX*0x2 + 0x418348]` at `0040efb8`). Read from those bases, every record is **`[id, x, y, width, height]`** in 8px cells, and `id` equals the record's index. The old parse took each entry's height from the *next* record and mislabelled the id as "next".

Consequences:
- **Every contact-sheet label in `pass4/` is off by one.** The art labelled `#N` there is code frame `#N+1` (and its height was wrong). The frame ids in the **Animations** table and in code-derived text (anim #66 → 163–168, anim #91 → 214) were already in code numbering. Ids quoted from the contact sheets (the **Key frames** list above) are not; add 1.
- **Open item 3 (building-piece off-by-one) is resolved.** Code indices map cleanly: floors 0–4 → pieces 12, 13, 10, 11, 9 = stone 224×56 at (0,104), stone 224×56 at (0,160), brick 224×48 at (0,0), brick 224×56 at (0,48), roof 224×160 at (288,800). The 48/56 heights match the floor "rows" exactly. Cells 0–4 → pieces 16, 2, 6, 14, 15 = plain window 24×48 at (272,0), NICELAND door 48×64 at (320,48), arched window 48×40 at (224,48), pediment windows 24×48 at (248,0) and (224,0).
- **Open item 2 (pane frames) is resolved at the endpoints.** Frames 163–168 are 16×16: 163 (304,0) full glass, 164 (304,16), 165 (320,16), 166 (304,32), 167 (320,32), 168 (320,0) full black. Pane state 0 = intact → 163 and state 5 = smashed → 168, consistent with "state is the frame index". The order of 1–4 follows the same rule; confirm visually.
- Falling brick = frames 4 (368,0,16×8) and 5 (384,0,16×16). Sill obstacle (anim #91) = frame 214 (920,0,32×8). Life icon = piece 17 (352,0,16×16).

## Hammer repair (2026-10-21)

**One completed hammer swing fixes the whole window.** `FUN_0040b510` (hammer start) records the current cell as the pending window only if its status `cell+0x7c` is non-zero. `FUN_0040bc80` (hammer complete) passes it to `FUN_00409a70`, which zeroes the status, decrements the broken counter and awards 100 / 500, then starts a 47-tick (`0x2f`) timer on the cell (probably the repair animation or score popup). Swinging at an intact window does nothing.

## Window damage sources (2026-10-21)

`FUN_00409840` callers: the intro script (`FUN_00401c78` heavy-damages a cell when Ralph's anim frame is 1; `FUN_00401e4c` / `FUN_00402510` light-damage with `(rand() & 0xff) > 0xe8`, about 9% per tick, while Ralph moves), bricks, and Ralph's section climb. The damaged cell is passed in a register, so **which window** is still unknown. The damage switch on cell type treats types 0, 3, 4 as pane windows; type 1 (**door**) keeps its own damage level (`cell[0x19]`, capped at 5), so **the door is damageable**.

## Remaining open items

1. The four per-cell floats `[0xd..0x10]` (1.0, 1.7, −1.5…−2.2). Likely jump parameters per window; not needed for a first rebuild.
2. ~~Pane state → frame mapping~~ endpoints resolved (see Table alignment correction); confirm 1–4 visually.
3. ~~Building-piece index alignment~~ resolved (see Table alignment correction).
4. Ralph drop-hazard sprite.
5. Which window the intro script and Ralph's climb damage (register-passed).
6. HUD layout details: score digits at x=240–328 is likely the attract/2-player layout, still unverified.

## Previously listed "still to decode" (now mostly resolved above)
### Original list

1. Ralph's gameplay movement and pound timing (`FUN_00402e00`, `FUN_0040d970`, `FUN_0040dd90`)
2. Nicelander appearance and pie logic (rand callers `FUN_00409360`, `FUN_00406e00`, `FUN_00407190`, `FUN_0040af70`)
3. Felix movement rules between cells, and what the four per-cell floats mean (obstacles, "BLOCK YOUR PATH" / "JUMP OVER")
4. Building layout per level: which floor types stack in which order, and how far the camera scrolls (`FUN_00405550`, `FUN_00409610`)
5. Section clear, scroll and roof sequences (`FUN_00402b94`, `FUN_00402cd8`)
6. Exact screen positions of windows and floors (the decompiler loses register-passed draw coordinates; may need disassembly)
