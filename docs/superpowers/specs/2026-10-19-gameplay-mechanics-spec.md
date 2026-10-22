# Fix-It Felix Jr. — Gameplay Mechanics Spec (evidence-tagged)

_Drafted 2026-10-19. **Revised 2026-10-21** with Ghidra pass 4 (`2026-10-19-ghidra-pass4-findings.md`, including its 2026-10-21 table-alignment, hammer-repair and damage-source sections). Replaces the guessed mechanics in `2026-06-17-fix-it-felix-pygame-design.md` wherever they conflict._

## Why this exists

The first implementation got the engine right (loading, font, input, timing, scenes) but built the game itself from guesses. Playtesting against reference footage showed the structure was wrong; pass 4 then decoded most of the real rules. Every claim is tagged with its evidence so we know what's settled.

## Evidence tags

| Tag | Source | Confidence |
|---|---|---|
| **[EXE]** | Our `FixitFelixJr.exe`: decompilation, disassembly, `.data` tables, strings | Ground truth for our build |
| **[REF]** | Mega Drive port footage (2013), via user screenshots | Strong for behavior; layout and numbers may differ (MD is landscape) |
| **[ATLAS]** | The art exists in `Data/felix0.png` | Proves an element exists, not how it's used |
| **[USER]** | User's decision or expectation | Requirement unless evidence contradicts it |
| **[ASSUMED]** | Inference with no direct evidence | Named constant, verify in play |
| **[OPEN]** | Unknown | Needs footage, a render check, or a decision |

Times assume 60 ticks/sec. Coordinates are in the 240×320 internal space **[EXE]**.

---

## 1. Coordinates and camera

- 240×320 is correct. **[EXE]** The world is a tall building drawn with a **vertical scroll offset** (`DAT_0041a248`). **[EXE]**
- World y: floors stack upward from **y = 320** (floor 0's bottom). Screen y = world y + scroll. **[EXE]**
- Sprites are clipped under a **24px top band** (`y < 0x18`), which is HUD space. **[EXE]**
- Sprite and building art come from two `.data` tables of `[id, x, y, w, h]` records in 8px cells: **216 sprite frames** at `0x418458`, **27 building pieces** at `0x418348`. **[EXE]** All frame/piece ids below are code ids from those tables.

## 2. Level structure

| Levels | Floors | Sections | Bird pairs / section | Sill obstacles / section | Ralph drop-hazards |
|---|---|---|---|---|---|
| 1–2 | 9 | 2 | 0 | 0 | 0 |
| 3 | 13 | 3 | 0 | 2 | 0 |
| 4 | 13 | 3 | 1 | 2 | 0 |
| 5 | 17 | 4 | 1 | 3 | 1 |
| 6 | 17 | 4 | 2 | 4 | 1 |
| 7–8 | 17 | 4 | 2 | 4 | 2 |
| 9+ | 17 | 4 | 2 | 4 | 3 |

**[EXE]** (`FUN_00409610`, table `0x419d78`, capped at level 10).

- **A section is 4 floors.** Section *s* is floors 4s…4s+3; Felix plays only on the active section's floors. **[EXE]**
- **Floor-type sequence, bottom to top [EXE]:**
  - levels 1–2: `0,1,2,3,2,3,2,2,4`
  - levels 3–4: `0,1,(2,3)×4,2,2,4`
  - levels 5+: `0,1,(2,3)×6,2,2,4`
- **Floor types [EXE]:**

  | Type | What | Height | Piece | Center cell |
  |---|---|---|---|---|
  | 0 | Ground (stone) | 56 | 12 | NICELAND door |
  | 1 | Second floor (stone) | 56 | 13 | Arched window |
  | 2 | Brick | 48 | 10 | Pediment window |
  | 3 | Brick | 56 | 11 | Pediment window |
  | 4 | Roof | 56 (layout) | 9 (224×160 art) | none |

  Which pediment piece (14 or 15) goes on type 2 vs type 3 is **[OPEN]**; how the 160px roof art sits on its 56px layout row is **[OPEN]**. Settle both on a rendered level.
- Floor art is drawn at **x = 8, 224 wide**, centered on the 240 screen. **[EXE]** The black margins either side are background. **[REF]**
- **Window x positions** (cell origin) **[EXE]**: floors 0–1 → 40, 72, 96 (48-wide center cell), 144, 176; floors 2–3 → 40, 72, 104, 144, 176. The 104 center sits 4px left of symmetric; check it on a render. **[OPEN]**
- Clouds, fire escapes, street furniture: art exists **[ATLAS] [REF]**; not in scope for the first rebuild.

## 3. Windows

- **5 cells per floor.** Cell kinds **[EXE]**: 0 plain (piece 16), 1 door (piece 2), 2 arched (piece 6), 3 and 4 pediment (pieces 14, 15). The roof has no cells.
- **Pane windows (kinds 0, 3, 4)** have a **top and bottom pane**, each in state **0 (intact) … 5 (smashed)**. The state is the frame offset: **pane frame = 163 + state** (163 full glass … 168 full black). **[EXE]** Endpoints confirmed; the look of 1–4 is **[OPEN — visual]**.
- **Door (kind 1)** keeps its own damage level 0–5. **[EXE]** It is drawn with door pieces 2–5 as damage rises; the level → piece mapping is **[ASSUMED]**.
- **Arched window (kind 2):** pieces 6 (intact) and 7 (damaged) exist **[EXE table]**; whether it can be damaged at all is **[OPEN]**. **Decision for the first rebuild: decorative, never damaged. [ASSUMED]**
- **Damage `FUN_00409840(heavy)` [EXE]:**
  - light: one random pane set to `rand()%5 + 1` (a **set**, so a smashed pane can come back as less damaged);
  - heavy: one pane set to 5.
- A window counts as **broken** while any pane (or the door's level) is non-zero.
- **Repair: one completed hammer swing fixes the whole window** (both panes to 0). **[EXE]** (`FUN_0040b510` → `FUN_0040bc80` → `FUN_00409a70`). Swinging at an intact window does nothing.
- **Scoring [EXE]:** **100** per window fixed, **500** if it was the **last broken window** in the section (`FIX LAST WINDOW 500 PTS`).
- **Section clear:** when the broken count reaches 0. **[EXE]**

## 4. Felix

- Stands on a window's sill; moves between the 5 cells of a floor and between the active section's 4 floors. **[EXE]**
- **Walk:** accelerates toward **±2.0 px/tick** and stops at the next cell. **[EXE]** The acceleration value is a runtime-initialized global (`_DAT_00416b80`): **0.5 px/tick² [ASSUMED]**.
- **Down** is blocked by a **sill obstacle** on the current cell and at the section's bottom floor. **[EXE]** (`FUN_0040b5e0`) **Up** is bumped back by a sill obstacle on the cell above (§8). **[EXE]** Up is refused at the section's top floor. **[ASSUMED]** (`FUN_0040b5e0` doesn't refuse it; the exe's jump probably rises and falls back to the same sill.)
- **Hammer:** existing raise/strike swing; on completion, fix the current window if broken (§3). **[EXE]**
- **Initial lives 10. [EXE] [USER: keep 10]**
- **Bonus life every 5000 points. [EXE string]**
- **Hit** (brick, bird, drop-hazard): knocked down, lose a life; existing stun mechanics. **[EXE]** Knocked-down frames exist (65–73 in old labels, so about 66–74). **[EXE table]**
- **Pie:** **480 ticks (8s) invulnerable**; bricks bounce off. **[EXE]**

## 5. Ralph

- Stands on the **top edge of the section's top floor** (ledge in front of the next floor up). **[EXE]** Starts at **x = 120**. **[EXE]**
- **States [EXE] (`0x40e1a4`):**
  - **Walk** at **1 px/tick**: off-center → go to **120**; at center → alternate **72** and **169** (patrol 120 → 72 → 120 → 169 → …).
  - **Pound** at each stop: **one brick every 9 + rand(0..7) ticks**. Pound duration is **[OPEN]**: **60 ticks [ASSUMED]**. After **every 3 walk/pound cycles**, a 30-tick timer, then a drop-hazard (levels 5+).
  - **Section pose** on section clear.
  - **Climb** after a section clear: slide to x = 120, climb **1 px/tick** to the new section's top; **every 10 ticks, 50% chance of light damage** to a window. **[EXE]** Which window is register-passed **[OPEN]**: **a random damageable cell on the floor at Ralph's height [ASSUMED]**.
  - **Rage** (Felix ate a pie): wait **80 ticks**, then **a brick every 8 ticks for 240 ticks**, then walk.
- **Level start:** the exe runs a scripted intro (Ralph walks in, heavy-damages a cell, ~9%/tick light damage while moving). The exact script is **[OPEN]**. **First rebuild: Ralph climbs from the street to his ledge using the section-climb rules, starting with one heavy hit to the door, then a 180-tick ready pause. [ASSUMED]** (The 180-tick pause is **[EXE]**, `FUN_004086e0`.)

## 6. Bricks

- **Spawn:** x = Ralph.x + rand(−32..31), y = Ralph.y + 8. **[EXE]**
- **Fall 1.9 px/tick**, straight down, no drift. **[EXE]** Art: frame 5 (16×16) with frame 4 (16×8). **[EXE table]**; how the two stack is **[ASSUMED]**.
- **Hit Felix:** brick vanishes, Felix is hit. Invulnerable Felix: brick **bounces off**. **[EXE]**
- **Break windows [EXE]:** from **level 2** on; only an **intact** window whose glass the brick overlaps, on the active section; **1-in-200 chance per tick** of overlap; light damage; brick vanishes. At most **4 breaks per counter period**; the reset point is **[OPEN]**: **reset each section [ASSUMED]**.
- **Ground** (world y ≥ 317): bounce out with vx = ±1.3, vy = −3.0, gravity 0.4/tick, blink, vanish. **[EXE]** The same bounce is used off an invulnerable Felix. **[ASSUMED]**
- **64 brick slots [EXE]**; the old `MAX_BRICKS = 4` cap was a misreading.

## 7. Nicelanders and pies

- A **Nicelander appears only in a window whose bottom pane is smashed (5)**, never on Felix's floor, never in the door or arched cell; random pick among up to 3 candidates; one of **6 characters**. **[EXE]**
- **Spawn timer [EXE]:** at 0, try to spawn (→ 1500 ticks); counts down while no Nicelander is out; at 0 with **fewer than 5 broken windows**, re-arm to 600. So pies only come while **5+ windows are broken**.
- The Nicelander rises into the pane (peek frames → bust **[ATLAS]**) and **the pie appears at the handoff frame**. **[EXE]**
- **Collecting** (Felix on the pie's cell): pie and Nicelander hidden, Felix invulnerable 480 ticks, **Ralph rages**. **[EXE]**
- How long an uncollected pie stays is **[OPEN]**: **until collected, the window is fixed, or the section clears [ASSUMED]**.

## 8. Hazards

- **Sill obstacles [EXE]** (level 3+): per section, placed on a random floor among the section's **top 3**, **max 2 per floor**, random non-arched cell; drawn at the sill center (frame 214), resting on top of the ledge **[USER]** (the exe hangs it 9 px lower, over the ledge's face). **Blocks dropping down from that cell, and bumps a jump up from the cell below:** sound 6, Felix falls back to his own sill, and the slab bounces −4, −2, −1 px for 4 ticks each. **[EXE]** That's the "BLOCK YOUR PATH" rule. What "JUMP OVER" refers to is **[OPEN]**.
- **Birds [EXE]** (level 4+): pairs per section, one from x = 272 (flipped) and one from x = −32, each on a random floor of the section's top 3; **0.5 px/tick**, wrap −32 ↔ 272; contact hits Felix unless invulnerable; removed on section clear.
- **Ralph drop-hazards [EXE]** (level 5+): up to the level limit (max 3 at once); spawned at Ralph's y + 8, aimed at a column near Ralph and a random floor of the section; fall 1.9 px/tick to that sill and stay; touching hits Felix, then it blinks 4 times and vanishes. Sprite **[OPEN]**.

## 9. Section clear and level end

- **Section clear [EXE]:** bricks cleared, birds removed, Ralph's section pose, "YOU FIXED IT!" **[EXE string]**, Ralph climbs (§5), then the **camera scrolls up 2 px/tick** by the new section's height, Felix moves up, the next section activates.
- **After the last section:** level end on the roof, then the next level after a 180-tick pause. **[EXE]** The roof sequence (medal descends, Nicelanders throw Ralph off) is **[REF] [ATLAS]**; its script is **[OPEN]**: **simple scripted sequence with assumed timings [ASSUMED]**. The level carries Felix's score **and lives** into the next. **[EXE, inferred]**: `FUN_004089b0` resets only the level, scroll and counters.
- Medal tier by level: **[ASSUMED]**, as in the current code.

## 10. HUD and front end

- **HUD layout [ASSUMED]:** the 24px top band holds score (`%06d` **[EXE]**), `LEVEL %d` **[EXE string]** and Felix-head life icons (piece 17). The exe's score digits at x = 240–328 are probably the attract/2-player layout. **[OPEN]**
- **Default high-score table:** 15000, 10000, 8000, 6000, 4000. **[EXE]** Default initials are **[OPEN]**: blank **[ASSUMED]**.
- Intro story (stump, bulldozers), attract mode and the arcade front end are **out of scope** for this rebuild. The current cutscene stays as is (the user has flagged it as wrong; separate task).

---

## Current implementation vs this spec

| Area | Current code | Spec |
|---|---|---|
| Level layout | One fixed grid on screen | Floors from the level table, 4-floor sections, camera scroll, roof |
| Window model | 3 whole-window states, one sprite | Two panes 0–5 per window; door level; per-kind art |
| Repair | Two hits (broken → cracked → intact) | One completed swing fixes the window |
| Window damage | Random scatter at level start | Ralph's climb, bricks (level 2+), intro door hit |
| Ralph | Fixed position, timed throws | Patrol / pound / rage / climb state machine |
| Bricks | 4 max, wrong sprite, no window breaks | 1.9 px/tick, spread spawn, window breaks, bounces |
| Pies | Random timed spawn, 10s super | Nicelander catch-up rule, 8s invulnerable, Ralph rage |
| Birds | Level 2+, timed | Level 4+, per-section pairs, 0.5 px/tick, wrap |
| Obstacles | None | Sill obstacles, drop-hazards |
| Scoring | +500 per fully fixed window; bonus every 10000 | +500 for the last window; bonus every 5000 |
| Level end | Separate level-clear screen; lives reset | Roof sequence in-game; lives carried |

**Kept as is:** asset loading, font, input (incl. pause), the 60 Hz fixed-step loop, scene manager, sound, Felix's hammer swing animation, stun/death flow, title / game-over / high-score scenes.
