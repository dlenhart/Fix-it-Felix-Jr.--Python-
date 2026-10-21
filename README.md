# Fix-It Felix Jr. — Reverse Engineering & Pygame Recreation

Rebuilding the Fix-It Felix Jr. arcade game in Python/Pygame by reverse-engineering the original Windows executable (`FixitFelixJr.exe`, 102KB, PE32, MSVC 2008, circa 2013).

This document covers the reverse engineering process — how we deconstructed the binary to extract the game constants, physics, state machines, and asset mappings needed to build a faithful recreation.

## The Binary

```
FixitFelixJr.exe  —  PE32 executable (GUI) Intel 80386, for MS Windows
Built with: MSVC 2008, OpenGL rendering, DirectSound audio
Internal resolution: 240x320 (portrait), displayed in a 640x480 window
Game loop: 60 ticks/sec fixed step (the 250ms SetTimer only updates the window title)
```

The game ships with its assets alongside the executable:
- `felix0.png` through `felix4.png` — 1024x1024 sprite atlases (5 palette variants)
- `hammer0.png` through `hammer3.png` — hammer effect atlases (4 color variants)
- `sound0.wav` through `sound29.wav` — 30 sound effects and music tracks
- `Controls.log` — input recording in 20-byte binary records

## Reverse Engineering Approach

We used [Ghidra](https://ghidra-sre.org/) (NSA's open-source reverse engineering framework) in headless mode, running automated decompilation scripts against the binary. Three progressively targeted passes extracted the game's internals over two sessions.

### Why Headless Ghidra?

The binary has no debug symbols and no source code. Rather than manually clicking through Ghidra's GUI, we wrote Java scripts that run via `analyzeHeadless` — Ghidra's CLI interface. This let us:

- Automate decompilation of specific functions by address
- Scan for string references and trace them to surrounding code
- Dump memory regions as typed values (int, float, pointer)
- Force function boundary creation at addresses the auto-analyzer missed
- Iterate quickly — re-running a script takes ~30 seconds vs. hours of manual work

### Setup

```
Ghidra 12.1.2:  ~/ghidra/ghidra_12.1.2_PUBLIC/
Java:           openjdk@21 via Homebrew
Project:        /tmp/ghidra_project/FixitFelix
Scripts:        tools/*.java
```

Base command to run any script:
```bash
export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk@21"

# First run (imports the binary and runs full analysis):
~/ghidra/ghidra_12.1.2_PUBLIC/support/analyzeHeadless \
  /tmp/ghidra_project FixitFelix \
  -import FixitFelixJr.exe \
  -postScript GhidraExtract.java \
  -scriptPath tools

# Subsequent runs (reuses existing analysis):
~/ghidra/ghidra_12.1.2_PUBLIC/support/analyzeHeadless \
  /tmp/ghidra_project FixitFelix \
  -process FixitFelixJr.exe \
  -postScript GhidraDeep.java \
  -scriptPath tools -noanalysis
```

## The Three Passes

### Pass 1 — Strings & Structure (`GhidraExtract.java`, `ghidra_extract.py`)

**Goal:** Find the game's constants by following string references backward into code.

**Method:** Search all defined strings in the binary for gameplay-related patterns (`"LEVEL"`, `"SCORE"`, `"GAME OVER"`, `"sound"`, `"felix"`, `"Controls"`, etc.). For each match, follow cross-references to the functions that use them, then decompile those functions to see the surrounding numeric constants.

Also scanned for `SetTimer`/`KillTimer` calls (to find the game tick rate) and ranked all functions by code size (largest functions are usually the game logic).

**Key discoveries:**
- `SetTimer(hWnd, 0, 0xFA, callback)` — first read as a 250ms (4 Hz) game tick. Pass 3 later showed the callback only updates the window title; playtesting at 4 Hz was unplayably slow, and every confirmed tick count (60 ticks per displayed second, 1800-tick high score entry) fits 60 Hz. Corrected to 60 ticks/sec.
- `_DAT_00424258 = 10` — initial lives are 10, not 3
- Internal resolution is 240x320 at 24bpp, not 640x480
- 5 section types with different row counts: `(type != 2) + 6`
- Score format `%06d`, high score charset is 38 characters
- 11 Felix states dispatched via function pointers, not 6
- 30 sound files loaded in a batch, 5 sprite atlas palettes

The Python version (`ghidra_extract.py`) was the initial prototype; the Java version (`GhidraExtract.java`) is the one that produced usable results.

### Pass 2 — Deep Decompilation (`GhidraDeep.java`)

**Goal:** Full decompilation of the 21 largest functions with no line limits.

**Method:** The first pass truncated decompiled output at 120 lines. Pass 2 removed that limit and targeted the 21 most-referenced and largest functions, plus scanned 20 known data addresses for initialized values.

**Key discoveries:**
- `FUN_0040a210` (3407 bytes) — the game init function. Sets lives to 10, allocates entity records, initializes the display system
- `FUN_0040c3d0` (1529 bytes) — the **state transition dispatcher**. A switch statement mapping state numbers 0-10 to callback function pointers. This was the Rosetta Stone for understanding Felix's state machine
- `FUN_00402780` (804 bytes) — level setup. Seeds RNG with `timeGetTime()`, configures section types, positions entities
- Entity record structure: 32 bytes with linked-list pointers, sprite data, x/y/z coords, animation frame, owner index, and flags (bit 0=visible, bit 2=flip horizontal)
- Section structure: 740 bytes with type, active flag, row count, row stride of 140 bytes
- Player state block: 3876 bytes (0xF24) per player

**Output:** 4,523 lines of decompiled C saved to `docs/ghidra-output/pass2.txt`.

### Pass 3 — Callback Functions & Physics (`GhidraPass3.java`, `GhidraPass3b.java`, `GhidraFloats.java`)

**Goal:** Decompile the 13 callback functions that contain the actual gameplay mechanics — movement speed, stun behavior, hammer timing, difficulty scaling.

**The problem:** These functions were reached only via function pointers stored by the state transition dispatcher. Ghidra's auto-analyzer didn't create function boundaries at these addresses because no direct `CALL` instruction targeted them. They showed up as `LAB_` labels (code labels inside larger unnamed blocks), not `FUN_` entries.

**Method (Pass 3):** First attempt used `getFunctionContaining()` and `getFunctionAt()` to find functions at 13 specific addresses. Only 3 of 13 were found — the rest fell in gaps between recognized functions.

**Method (Pass 3b):** Used `CreateFunctionCmd` to **force Ghidra to create function definitions** at each address. This tells the decompiler "treat the code starting here as a function entry point" — even though no `CALL` instruction targets it. All 10 previously-missing functions were successfully created and decompiled. Also decompiled the 3 parent functions that contain the callback targets.

**Method (GhidraFloats):** Targeted scan of `.data` section addresses referenced by the decompiled callbacks. Read raw bytes and interpreted them as both integers and IEEE 754 floats to identify movement constants.

**Key discoveries:**

The movement system uses **float-based velocity/acceleration physics**, not grid snapping:

| Constant | Value | Source |
|----------|-------|--------|
| Max horizontal speed | 2.0 px/tick | `_DAT_00416b40` |
| Initial vertical velocity | 0.2 px/tick | `_DAT_00416b88` |
| Jump initial X velocity | -5.0 px/tick | `_DAT_00416c00` |
| Fall terminal velocity | 8.0 px/tick | `_DAT_00416b58` |
| Hammer start offset | -7.0 | `_DAT_00416b68` |
| Stun knockback Y position | 480 (above 320px screen) | `0x1e0` |
| Brick fall speeds | -1.5 to -2.2 px/tick | `_DAT_00416b98/ba4/ba8/ba0` |
| Bird speed | X=2.2, Y=-4.0 px/tick | `_DAT_00416b94/b90` |

Stun is **position-based recovery** — Felix gets knocked to y=480 (above the 320px screen) and falls back down. It's not a timer countdown.

Jump uses a **parabolic arc** with a sqrt-based divisor for the trajectory calculation.

Some constants (acceleration rates, tick deltas, Y bounds) are zero in the binary's `.data` section because they're written at runtime by the init function through pointer arithmetic. These will be estimated and calibrated during playtesting.

**Output:** 6,184 total lines across three output files saved to `docs/ghidra-output/`.

## Tools Reference

| Script | Language | Purpose |
|--------|----------|---------|
| `tools/ghidra_extract.py` | Jython | Initial prototype — string search + decompilation (Ghidra's Jython API) |
| `tools/GhidraExtract.java` | Java | Pass 1 — string refs, timer calls, largest functions, top-10 decompilation |
| `tools/GhidraDeep.java` | Java | Pass 2 — full decompilation of 21 named functions + global data scan |
| `tools/GhidraPass3.java` | Java | Pass 3 — targeted decompilation at 13 callback addresses (3/13 found) |
| `tools/GhidraPass3b.java` | Java | Pass 3b — `CreateFunctionCmd` to force function creation, all 10 remaining + 3 parents |
| `tools/GhidraFloats.java` | Java | Float scan — read `.data` section at specific addresses as IEEE 754 floats |

## Output Files

| File | Lines | Content |
|------|-------|---------|
| `docs/ghidra-output/pass2.txt` | 4,523 | 21 decompiled functions + global constant scan |
| `docs/ghidra-output/pass3.txt` | 667 | 3 callback functions + float globals + player state data |
| `docs/ghidra-output/pass3b.txt` | 994 | 10 force-created callback functions + 3 parent functions |
| `docs/superpowers/specs/2026-06-17-ghidra-analysis-findings.md` | — | Consolidated analysis with all corrections and verified constants |

## What We Learned (vs. What We Assumed)

| Topic | Original Assumption | Ghidra Reality |
|-------|-------------------|----------------|
| Resolution | 640x480 | 240x320 portrait, scaled up |
| Game tick | 60 FPS | 60 ticks/sec — briefly misread as 250ms (4 Hz) from a window-title timer, corrected after playtesting |
| Lives | 3 | 10 |
| Grid rows | 3 per section | 6-7, varies by section type |
| Section types | 3 identical | 5 different configurations |
| Felix states | 6 | 11 with function-pointer dispatch |
| Movement | Grid snapping | Float velocity/acceleration physics |
| Stun | Timer countdown | Position-based knockback recovery |
| Jump | Linear interpolation | Parabolic arc (sqrt trajectory) |
| Brick speed | Variable guess | 4 specific speeds: -1.5 to -2.2 px/tick |

## Project Status

All reverse engineering is complete. The implementation plan (`docs/superpowers/plans/`) has been updated with every verified constant and the corrected physics model. The Pygame recreation has not started yet — next step is writing code.

## How to Reproduce

1. Install Ghidra 12.1.2+ and Java 21
2. Place `FixitFelixJr.exe` in the project root
3. Run the import + analysis:
   ```bash
   export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
   export JAVA_HOME="/opt/homebrew/opt/openjdk@21"
   ~/ghidra/ghidra_12.1.2_PUBLIC/support/analyzeHeadless \
     /tmp/ghidra_project FixitFelix \
     -import FixitFelixJr.exe \
     -postScript GhidraExtract.java \
     -scriptPath tools
   ```
4. Run subsequent passes with `-process` instead of `-import` and `-noanalysis`
