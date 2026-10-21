# Fix-It Felix Jr. — Ghidra Binary Analysis Findings

## Overview

Full decompilation of `FixitFelixJr.exe` (102KB, MSVC 2008, x86) using Ghidra 12.1.2 headless analysis. 21 functions decompiled, 4,411 lines of C output. This document records every confirmed game constant and corrects assumptions made in the original design spec.

---

## Corrections to Original Assumptions

### 1. Internal Resolution: 240x320, NOT 640x480

The game renders internally at **240x320 pixels at 24bpp**, NOT 640x480.

**Evidence:**
```c
DAT_00420384 = 0xF0;    // width = 240
_DAT_00420388 = 0x140;  // height = 320
_DAT_0042038e = 0x18;   // 24 bits per pixel
DAT_00420394 = 0x38400; // image size = 240 * 320 * 3 = 230400
DAT_00420284 = 0x2D0;   // stride = 720 bytes = 240 * 3
```

Mouse coordinate mapping confirms:
```c
game_x = (mouse_x * 0xF0) / window_width;   // 0xF0 = 240
game_y = (mouse_y * 0x140) / window_height;  // 0x140 = 320
```

The 640x480 window is just the display size — the game scales up from 240x320. Note: the game is **taller than wide** (portrait orientation, 240 wide x 320 tall). The boot loader BMPs are 640x480 landscape, but the actual gameplay runs portrait.

### 2. Game Tick Rate: 60 ticks/sec (CORRECTED — originally misread as 250ms / 4 FPS)

```c
timeBeginPeriod(1);
SetTimer(hWnd, 0, 0xFA, FUN_00413de0);  // 0xFA = 250ms
```

**Correction (2026-10-19):** Pass 1 read this 250ms timer as the game tick and concluded logic ran at 4 ticks/sec. Pass 3 decompiled the callback `FUN_00413de0` and found it is only the **window title updater / Controls.log recorder** (see "Timer Callback" below) — it does not drive game logic. `timeBeginPeriod(1)` alongside it requests 1ms timer resolution, which points to a separately self-paced main loop.

Game logic runs at **60 ticks/sec**. The main loop's pacing call wasn't decompiled, so 60 Hz is inferred, but every confirmed tick-count only makes sense at that rate:
- 1 displayed "second" (TIME LEFT) = 60 ticks = 1 real second (at 4 Hz: 15s)
- High score entry timer: 1800 ticks = 30 seconds (at 4 Hz: 7.5 minutes)
- D-pad repeat delay: 20 ticks = 0.33 seconds (at 4 Hz: 5s)
- Felix max horizontal speed 2.0 px/tick crosses a 40px window in 0.33s (at 4 Hz: 5s)

Playtesting at 4 Hz confirmed it: movement and falling bricks were unplayably slow.

### 3. Initial Lives: 10, NOT 3

```c
_DAT_00424258 = 10;  // Set during game init
```

### 4. Window Grid: 5 Columns x 5-7 Rows, NOT 5x3

**5 columns confirmed:**
```c
puVar3[0x13] = 5;  // window columns per row
```

**Rows per section vary by type:**
```c
rows = (section_type != 2) + 6;
// Type 2: 6 rows
// Types 0, 1, 3, 4: 7 rows
```

### 5. Section Types: 5 Different Configurations, NOT 3 Identical Sections

The game has **5 section types** (0-4), each with different window row patterns:

| Type | Rows | Height | Row Pattern |
|------|------|--------|-------------|
| 0 | 7 | 12 | (0,0), (1,0), (2,1), (3,0), (4,0) |
| 1 | 7 | 13 | (0,0), (1,0), (2,2), (3,0), (4,0) |
| 2 | 6 | 10 | (0,3), (1,3), (2,4), (3,3), (4,3) |
| 3 | 7 | 11 | (0,3), (1,3), (2,4), (3,3), (4,3) |
| 4 | special | 9 | 5 sub-rows with explicit entity setup |

Row types (the second number in each pair) define different window configurations:
- Type 0: empty/plain
- Type 1: normal windows (variant A)
- Type 2: normal windows (variant B)
- Type 3: brick/breakable windows (variant A)
- Type 4: brick/breakable windows (variant B)
- Type 5: null/empty

### 6. Player States: 11 States, NOT 6

| State | Description |
|-------|-------------|
| 0 | Idle/Standing |
| 1 | Walking (direction A) |
| 3 | Walking (direction B) |
| 4 | Jumping/Moving to position |
| 5 | Hammering (initial) |
| 6 | Hammering (extended) |
| 7 | Falling/sliding |
| 8 | Stunned/hit |
| 9 | Dead/dying |
| 10 | Death handler (checks lives, plays sounds) |

### 7. Game State Machine: 11 States, NOT 6 Scenes

| State | Description | Timer/Duration |
|-------|-------------|----------------|
| 0 | Title/Attract mode | — |
| 1 | Level start | — |
| 2 | High score table display | 900 ticks (15 sec) |
| 3 | Gameplay active | `DAT_00418064 = 0x6F` (111) |
| 4 | Player switch (2P) | — |
| 5 | Level complete | — |
| 6 | Network setup | — |
| 7 | New game start | 300 ticks (5 sec) |
| 8 | High score entry | 1800 ticks (30 sec) |
| 9 | Instructions/Demo | — |
| 10 | Title screen setup | Hides 9 UI elements |

### 8. High Score Character Set: 38 Characters, NOT 26

```
" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."
```
Includes space, A-Z, 0-9, and period (38 total).

### 9. Sound Index Mappings (Partial Confirmation)

From the decompiled code, specific sound indices are used:
- Sound 0x0F (15): movement/state transitions → our mapping: "felix_move" ✓
- Sound 0x11 (17): hammer extended → our mapping: "felix_stunned" ✗ (should be hammer-related)
- Sound 0x13 (19): death/game over → our mapping: "nicelander_alt" ✗ (should be death)

### 10. Brick Entities: 4 Per Level, NOT Variable

The level setup allocates exactly **4 brick entity pairs** (front + back), with fixed positions relative to the building.

### 11. Window Entities: 32 Per Player

```c
iVar7 = 0x20;  // 32 window entities allocated per player
```

### 12. Score Display: 5 Digits at Specific Positions

5 score digit sprites, spaced 22 pixels apart starting at x=240:
```
Digit 0: x=240, Digit 1: x=262, Digit 2: x=284, Digit 3: x=306, Digit 4: x=328
```
Y position: 318, Z-order: 120

---

## Confirmed Assumptions (Correct in Original Spec)

| Assumption | Status | Evidence |
|-----------|--------|----------|
| Scoring: 100 pts per fix, 500 pts per full window | ✓ Confirmed | "FIX WINDOW 100 PTS", "WINDOW 500 PTS" strings |
| 5 felix palette variants (felix0-4) | ✓ Confirmed | Loading loop with color key assignments |
| 4 hammer variants (hammer0-3) | ✓ Confirmed | Loading loop with color key assignments |
| 30 sound files (sound0-29) | ✓ Confirmed | Batch load size 0x1E = 30 |
| 5 high score entries | ✓ Confirmed | Loop bound `iVar1 < 5` |
| 3-character initials | ✓ Confirmed | Position cycles 0, 1, 2 |
| 20-byte high score records | ✓ Confirmed | Stride 0x14 |
| Controls.log: 20-byte records | ✓ Confirmed | `fwrite(ptr, 0x14, count, file)` |
| Level displayed 1-indexed | ✓ Confirmed | `sprintf("LEVEL %d", level + 1)` |
| Level 10 threshold | ✓ Confirmed | `if (level < 10)` branch |
| Score format %06d | ✓ Confirmed | `sprintf("%06d", score)` |
| Keyboard input + joystick | ✓ Confirmed | GetKeyState + button bit masks |
| 2-player alternating support | ✓ Confirmed | `DAT_00424240 = 1 - DAT_00424240` swap |

---

## Data Structure Details

### Entity Record (32 bytes / 0x20)

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 4 | Linked list prev pointer |
| 0x04 | 4 | Linked list next pointer |
| 0x08 | 4 | Texture/sprite data pointer |
| 0x0C | 2 | X coordinate |
| 0x0E | 2 | Y coordinate |
| 0x10 | 2 | Z-order / priority |
| 0x12 | 2 | Animation frame index |
| 0x14 | 2 | Texture frame count |
| 0x16 | 2 | Unknown |
| 0x18 | 2 | Owner/player index (0xFFFF = global) |
| 0x1A | 2 | Flags (bit 0=visible, bit 2=flip H) |

### Section Structure (740 bytes / 0x2E4)

| Offset | Field |
|--------|-------|
| 0x2C4 | Section type (0-4) |
| 0x2C8 | Active flag (1) |
| 0x2CC | Start row offset |
| 0x2D0 | Row count (6 or 7) |
| 0x2D8 | Initialized to 0 |
| 0x2DE | Short: 0 |
| 0x2E0 | Short: 1 |

Row stride within section: 0x8C (140) bytes per row.

### Player State Block (3876 bytes / 0xF24)

| Offset | Field |
|--------|-------|
| +0x000 | Player active flag |
| +0x008 | Current level (0-indexed) |
| +0x004 | Lives remaining |
| +0xEE0 | Display flag |

### Texture Color Keys

| Texture | Color Key (R,G,B,A) | Purpose |
|---------|---------------------|---------|
| felix0 | (255,255,0,255) yellow | Default palette |
| felix1 | yellow + (0,255,0,255) green | Green variant |
| felix2 | (255,255,255,255) white | White variant |
| felix3 | yellow + (0,255,255,255) cyan | Cyan variant |
| felix4 | Special palette (skips indices 0xF5-0xF7) | Special variant |
| hammer0 | (255,0,0,255) red | Red effects |
| hammer1 | (0,255,0,255) green | Green effects |
| hammer2 | (255,255,255,255) white | White effects |
| hammer3 | (0,255,255,255) cyan | Cyan effects |

---

## Pass 3 Findings — Callback Functions & Movement System

All 13 target callback functions were successfully decompiled by force-creating function boundaries at the LAB_ addresses. Output saved to `docs/ghidra-output/pass3.txt`, `pass3b.txt`, and `pass2.txt`.

### State → Callback Function Mapping (Confirmed)

| State | Callback | Sprite Set | Purpose |
|-------|----------|-----------|---------|
| 0 | FUN_0040b5e0 (767 bytes) | DAT_00419830 | Idle — input processing |
| 1 | FUN_0040b8e0 (260 bytes) | DAT_0041986c | Walk A — horizontal/vertical traverse |
| 3 | FUN_0040b9f0 (647 bytes) | DAT_0041986c | Walk B — inter-row movement with accel |
| 4 | FUN_0040bd90 (268 bytes) | DAT_00419890 | Jump — arc trajectory with sqrt |
| 5 | FUN_0040bea0 (422 bytes) | DAT_00419890 | Hammer — swing with phase timing |
| 6 | FUN_0040c0d0 (194 bytes) | DAT_00419890 | Hammer extended — gravity fall |
| 7 | FUN_0040c050 (127 bytes) | DAT_00419890 | Fall — terminal velocity capped |
| 8 | FUN_0040bc80 (271 bytes) | DAT_00419878 | Stun — position-based recovery |
| 9 | FUN_0040c0d0 (shared) | DAT_004198a8 | Dying — same code as state 6 |
| 10 | LAB_0040c1a0 | — | Death handler — sound 0x13/0x0F, respawn |

FUN_0040c3d0 (1529 bytes) is the universal state transition dispatcher. It stores the callback function pointer at player offset +0x08 (DAT_00421758), resets velocities, and plays the transition sound.

### Movement System Architecture

The game uses **float-based velocity/acceleration physics**, not grid snapping. Player state block (0xF24 bytes per player) key offsets:

| Offset | Type | Field |
|--------|------|-------|
| +0x00 (0x21750) | int* | Current window pointer |
| +0x04 (0x21754) | int* | Saved window (for stun recovery) |
| +0x08 (0x21758) | code* | State callback function pointer |
| +0x0C (0x2175c) | float | Y position |
| +0x10 (0x21760) | float | X position |
| +0x18 (0x21768) | float | Y velocity |
| +0x1C (0x2176c) | float | X velocity / accumulator |
| +0x2C (0x2177c) | int | Knockback Y (set to 0x1e0=480 on stun) |
| +0x30 (0x21780) | int | Current state number |
| +0x44 (0x21794) | short | Can-act flag |
| +0x48 (0x21798) | short | Can-hammer flag |
| +0x4C (0x2179c) | short | Hammer phase flag |
| +0x50 (0x217a0) | short | Hit/damage flag (→ death if set) |
| +0x54 (0x217a4) | short | Stun recovery flag |
| +0x70 (0x217c0) | short | Stun state counter |

### Float Constants (Compile-Time, from .data section)

| Address | Float Value | Used By | Purpose |
|---------|------------|---------|---------|
| _DAT_00416b40 | **2.0** | States 0,3 | Max horizontal speed (right) |
| _DAT_00416b44 | **-2.0** | States 0,3 | Max horizontal speed (left) |
| _DAT_00416b88 | **0.2** | State 0 | Initial vertical velocity (down/toward bottom) |
| _DAT_00416b8c | **-0.2** | State 0 | Initial vertical velocity (up/toward top) |
| _DAT_00416b08 | **-6.0** | State 1 | Walk start horizontal reset |
| _DAT_00416b58 | **8.0** | State 6/9 | Max fall speed (terminal velocity) |
| _DAT_00416b68 | **-7.0** | State 5 | Hammer initial vertical offset |
| _DAT_00416c00 | **-5.0** | State 4 | Jump initial X velocity |
| _DAT_00416c04 | **10.0** | State transition | Default local_c (jump arc divisor) |
| _DAT_00416b94 | **2.2** | Entity setup | Bird/entity X velocity |
| _DAT_00416b90 | **-4.0** | Entity setup | Bird/entity Y velocity |
| _DAT_00416b98 | **-1.8** | Entity setup | Brick fall Y velocity (type A) |
| _DAT_00416ba4 | **-2.2** | Entity setup | Brick fall Y velocity (type B) |
| _DAT_00416ba8 | **-1.7** | Entity setup | Brick fall Y velocity (type C) |
| _DAT_00416ba0 | **-1.5** | Entity setup | Brick fall Y velocity (type D) |
| _DAT_00416b9c | **1.7** | Entity setup | Brick drift X velocity |
| _DAT_00416be8 | denorm | State 6/9 | Gravity acceleration (≈0, runtime-set) |
| DAT_00416b48 | **232.0** | Position | Y coordinate (near screen bottom) |
| DAT_00416bac | **317.0** | Position | Y coordinate (bottom boundary) |
| DAT_00416bbc | **304.0** | Position | Y coordinate (lower play area) |
| DAT_00416bd0 | **170.0** | Position | Y coordinate (mid screen) |
| DAT_00416bb8 | **32.0** | Entity | Entity width |

### Runtime-Initialized Globals (Zero in Binary)

These are set by FUN_0040a210 (game init, 3407 bytes) at startup. Values are 0 in the .data section:

| Address | Referenced By | Probable Purpose |
|---------|-------------|-----------------|
| _DAT_00416b18 | States 1,4,5,7 | Per-tick delta (velocity step per frame) |
| _DAT_00416b10 | State 1 | Vertical movement rate for walk |
| _DAT_00416b80 | State 3 | Horizontal acceleration rate |
| _DAT_00416b78 | State 5 | Hammer animation rate per tick |
| _DAT_00416b70 | State 5 | Hammer phase threshold |
| _DAT_00416b60 | State 5 | Hammer hit detection offset |
| _DAT_0042425c | States 0,3 | Y position upper bound |
| _DAT_00424260 | States 0,3 | Y position lower bound |

### Input Bitmask (from State 0 — FUN_0040b5e0)

Input = `DAT_0041db00 | DAT_0041be14` (keyboard OR joystick)

| Bit | Action | Transition |
|-----|--------|-----------|
| 0x01 | Hammer | → State 5 |
| 0x02 | Interact/jump down | → State 6 |
| 0x04 | Up | → State 3 (vel = -0.2) |
| 0x08 | Down | → State 3 (vel = +0.2) |
| 0x20 | (Flag at DAT_00424270) | → State 4 |
| 0x40 | Jump/action | → State 4 or 8 (context-dependent) |

### Stun Mechanics (State 8 — FUN_0040bc80)

- **Not timer-based** — position/animation-driven recovery
- On stun: Y position set to `0x1e0` (480), above the 320px screen (knockback upward)
- Recovery condition: reach target window position AND stun counter (DAT_004217c0) clears
- If hit flag (DAT_004217a0) set during stun → transition to state 9 (death)
- Otherwise → back to state 0 (idle) via FUN_00409ac0

### Hammer Mechanics (State 5 — FUN_0040bea0)

- Hammer starts at Y offset -7.0 (DAT_00416b68)
- Phase 1: Hammer descends, accumulator decremented by DAT_00416b78 per tick
- Phase 2: When accumulator < threshold (DAT_00416b70), sets phase flag (DAT_0042179c = 1)
- Then adds per-tick delta (DAT_00416b18) — moves hammer into collision range
- Collision check: FUN_00405e10 → FUN_004097d0 (repair window)
- Section type 4 has special hammer behavior
- If collision after threshold: reset and transition to state 9 (recovery)

### Jump Mechanics (State 4 — FUN_0040bd90 + FUN_0040c3d0 case 4)

- Initial X velocity = _DAT_00416c00 = **-5.0**
- Y velocity = `(target_Y - current_Y) / arc_divisor`
- Arc divisor involves `_CIsqrt()` — parabolic jump trajectory
- On landing (collision detected by FUN_0040b410): snap to window, set horizontal velocity to ±2.0, transition to state 0
- Y clamped between _DAT_0042425c and _DAT_00424260

### Fall Mechanics (State 7 — FUN_0040c050)

- Per tick: X velocity += DAT_00416b18 (delta), Y += velocity, X += X_vel
- Collision check each tick via FUN_0040b410
- On landing: snap to window position, zero velocities, transition to state 0

### Level Setup (FUN_00402780, 804 bytes)

- Seeds RNG: `srand(timeGetTime())` normally, or `srand(0xd80da1)` for deterministic replay (when DAT_004242a4 != 0)
- Section height: `section_type * 8 + 0x1c` (range: 28-60)
- Ralph positioned at Y = 0x5A (90 decimal)
- Entity velocities per type (from entity setup switch):
  - Type 1: X=2.2, Y=-4.0 (fast entity, likely bird)
  - Type 2: X=2.0, Y=-1.8 (medium brick)
  - Type 3: X=1.0, Y=-1.7/-2.2 (directional brick)
  - Type 4: varied (special section)

### Timer Callback (FUN_00413de0, 498 bytes)

This is the **window title updater**, not the main game tick handler:
- Sets window title via `SetWindowTextA`
- Records up to 100 button states for Controls.log
- Appends `[score=X,Y]` format
- Checks `GetKeyState(0x91)` (Scroll Lock) for debug mode

### Death Handler (State 10)

- If lives == 0: calls `FUN_0040f4a0(0)` then plays sound 0x13 (death/game over), sets game-over flag
- If lives > 0: plays sound 0x0F (respawn), calls FUN_0040e1d0 (reset position)

### Remaining Unknowns

After three passes, these are still not directly extractable from static analysis:

- **Bonus life score threshold**: Not found as a hardcoded constant. May be computed from level/section data or stored in an un-decompiled function
- **Super Felix duration**: Not found in any decompiled callback. May be set by pie collection handler (not decompiled)
- **Pie spawn timing**: Lives in the main game loop dispatcher (not in any callback we decompiled)
- **Brick throw interval**: Controlled by the game loop tick handler, not in individual callbacks
- **Exact acceleration rates**: Set at runtime by init function through pointer arithmetic — the computed values couldn't be statically determined

These will need to be estimated during implementation and calibrated through playtesting against the original game.
