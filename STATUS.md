# Fix-It Felix Jr. — Implementation Status

_Last updated: 2026-10-19_

## Done — Tasks 1-14 (all reviewed, all committed)

The full game loop is wired and working, with real sprites: **Title → Cutscene → Game → Level Clear → Game Over → High Scores → Title.**

| # | Task | What it built |
|---|------|----------------|
| 1 | Project scaffold | `src/constants.py`, `src/scene_manager.py`, `src/main.py` — 240×320 internal resolution, fixed-step game loop (now 60 ticks/sec — see below), rendered at 60fps |
| 2 | Input handler | `src/input_handler.py` — unified keyboard + gamepad input |
| 3 | Sprite sheet system | `src/sprite_sheet.py`, `src/sprite_data.py` (scaffold), `tools/sprite_viewer.py` — atlas loader + manual sprite-mapping tool (superseded, see Task 14) |
| 4 | Font renderer | `src/font_renderer.py` — bitmap font from the atlas |
| 5 | Sound manager | `src/sound_manager.py` — all 30 WAV files mapped to game events |
| 6 | Building & window grid | `src/entities/building.py` — window damage/repair state machine |
| 7 | Felix entity | `src/entities/felix.py` — movement, hammering, stun, scoring (float-based physics per Ghidra RE) |
| 8 | Ralph & bricks | `src/entities/ralph.py`, `src/entities/brick.py` — brick-throwing AI and collision |
| 9 | Bird & pie | `src/entities/bird.py`, `src/entities/pie.py` — hazard and power-up entities |
| 10 | GameScene integration | `src/scenes/game_scene.py` — wires every entity into the playable loop |
| 11 | Title scene | `src/scenes/title_scene.py` |
| 12 | Game over & high scores | `src/scenes/game_over_scene.py`, `src/scenes/high_score_scene.py` — JSON persistence to `scores.dat` |
| 13 | Level clear & cutscene | `src/scenes/level_clear_scene.py`, `src/scenes/cutscene_scene.py` — closes the full loop |
| 14 | Sprite coordinates | `src/sprite_data.py` populated — **done automatically**, not via manual dragging (see below) |

### How Task 14 actually got done

The atlas PNGs turned out to have a genuinely transparent background around each sprite, so instead of manual click-dragging in `tools/sprite_viewer.py`, I wrote `tools/sprite_autodetect.py` — it scans the alpha channel and finds every isolated sprite's exact pixel bounding box automatically (connected-component flood fill). More precise than a mouse. 69 coordinate frames across 39 of 41 sprite categories are now populated with real, measured coordinates; `shutter_left`/`shutter_right` are the only two left empty (no matching art exists in the atlas for them, and neither is used by current game code — no impact).

**Worth double-checking when you play:** the exact Felix/Ralph animation-frame semantics (which of the ~59 similar unlabeled frames is "walk" vs "climb" vs "stunned") were assigned by visual judgment, not guaranteed fidelity to the original arcade's frame timing. Nothing should look broken, but a pose might look slightly off — easy to swap coordinates in `sprite_data.py` if so.

## Done — Task 15 (partial)

- ✅ `MAX_BRICKS = 4` on-screen brick cap now actually enforced
- ✅ Super Felix visual indicator (was already built in Task 7)
- ✅ Window caption set

**Left for you** (needs ears/hands, not something I can do):
- Listen to each `Data/soundN.wav` and check it against the mapping in `src/sound_manager.py`'s `SOUND_MAP`/`MUSIC_MAP` — swap anything that sounds wrong.
- Play a few levels and see if the difficulty curve feels right. Tuning knobs: `src/entities/ralph.py`'s `configure_for_level()` (brick throw rate/aim/volume) and `src/scenes/game_scene.py`'s bird/pie spawn intervals.
- A full playthrough — now that real sprites are in, this is the first point where an actual look-and-feel pass makes sense.

## Fixed after first playtest

- `8e7c4da` — Title logo was missing "JR." (bbox too narrow, cut it off) — widened.
- `8e7c4da` — Font digit "1" rendered as "/" everywhere (a duplicate entry in `font_renderer.py`'s character map overwrote the correct glyph) — removed the duplicate.
- `6ea5fb1` — **Arrow keys / Space / Enter barely worked at all.** Real bug, not a controls question: `InputHandler.poll()` runs once per render frame (60fps) and cleared its "just pressed" signal every call, but game logic only checks it once per 250ms tick (4Hz, ~every 15 render frames) — so a key press was almost always cleared before any tick got a chance to see it. Fixed by having "just pressed" latch across polls until a tick explicitly consumes it. Verified with a headless simulation of the exact worst-case timing, end-to-end through `GameScene`/`Felix`.
- `d79199b` — **Scaled UI text overflowing the screen** — "I'M GONNA WRECK IT!" was clipped to "WRECK I" in the cutscene. Found this was systemic: 6 different strings across the cutscene, game over, level clear, and high score screens all scale text by a fixed factor regardless of length, and several overflow the 240px canvas. Added a `scale_text_to_fit()` helper and fixed every affected call site. Also fixed a separate bug found along the way: the high-score table was positioned at a fixed x=120 instead of centered, so roughly half of it always rendered off-screen.
- `ae54332` — **Felix's walk/idle/hammer sprites (and the birds) were left/right-swapped.** Task 14's automated pose categorization got these backwards — confirmed by direct pixel inspection (e.g. "hammer_right" actually leaned/faced left). Swapped the coordinates back.
- `ab8a7c9` — **Movement looked choppy/laggy, not just slow.** Real cause: position only updated once per 250ms game tick (4Hz), but rendering happens every frame at 60fps — so ~15 identical frames, then a sudden jump, repeating. Added proper render interpolation (smoothing between ticks) for Felix, bricks, and birds, so motion is visually smooth at 60fps while game logic still runs at its original 4Hz rate. Collision/gameplay code is unaffected — it still uses the true, non-interpolated position.
- `2ca59e5` — **Horizontal movement still felt slow after the interpolation fix** — because the pace itself (5 real seconds to cross one window) was unchanged, just smoother. That pace was the Ghidra-confirmed original value, so this was a deliberate feel/balance decision, not a bug — user explicitly chose to speed it up. `FELIX_MAX_HORIZONTAL_SPEED` raised from 2.0 to 5.0 px/tick (5.0s → 2.0s per window), documented in the constant's comment as an intentional deviation from the historically-accurate value.
- `4473eeb` — **Ralph's thrown bricks barely fell before hitting the top window row** (user compared against a reference screenshot of the original game). Two causes: bricks spawned only ~2px of actual travel room above the collision threshold (Ralph's feet sit right at the roofline already, so there was little headroom to begin with — spawn point moved closer to his raised arm to use the full available gap), and the collision check stopped bricks at *any* window row including already-fully-broken ones with no glass left (now passes through those). Bricks now fall 31-66px over 3-9.5 real seconds instead of ~2px in half a second — verified both by simulation and by rendering and visually inspecting an actual mid-flight frame.

## Game ran 15× too slow — tick rate corrected to 60/sec (uncommitted)

**Symptom:** "The game is horribly slow" — Felix's left/right and Ralph's falling bricks both crawled.

**Root cause:** The game logic ran at 4 ticks/sec because the early Ghidra pass misread a 250ms `SetTimer` as the game tick. Pass 3 had already shown that timer's callback only updates the window title, but the 4 Hz conclusion was never revisited. Every confirmed tick count fits 60 Hz instead (60 ticks per displayed second, 1800-tick = 30s high-score entry, Felix's 2.0 px/tick = 0.33s per window).

**What changed:**
- `TICK_RATE` is now 1/60s. Ghidra per-tick velocities are used as-is, and Felix's speed is back to the original 2.0 (the earlier 5.0 bump was compensating for the wrong tick rate).
- Every estimated duration lives in `src/constants.py`, written in seconds via `seconds_to_ticks()` — tune feel there. No more magic tick numbers in scenes/entities.
- Sprite animation (Felix walk, Ralph, birds) and the pie's blink use a frame-hold cadence so they don't flicker at 60 ticks/sec.
- **Bricks no longer break windows.** They used to break the first unbroken window they touched and vanish — nearly always the top row, so they almost never reached Felix. They now fall the full building height (~2.4-3.6s) and only threaten Felix, like the arcade original. They also fall straight down (no random sideways drift — at 60 Hz it carried bricks off the building).
- Docs corrected: Ghidra findings §2, README, design spec note.

**Measured (headless sim):** one window sideways 0.35s, one row 0.43s, hammer swing 0.35s, stun recovery 1.4s, cutscene 11s, game over 3s, level clear 5s, high-score table 15s (Ghidra's 900 ticks).

## Fixed after third playtest (uncommitted)

- **UP/DOWN were inverted** — row 0 is the bottom row, but UP moved toward row −1, so UP did nothing from the street and DOWN climbed. Pre-existing since Task 7. Flipped in `src/entities/felix.py`.
- **Grey bar down the left edge** (plus grey stripes beside Ralph and stray ledges either side of the building) — the `wall_brick` tile was cut from the building's corner, including its grey pillar and ledge, and got tiled across the whole background. Re-cut to a pure-brick 64×48 region that tiles seamlessly.
- **Score looked broken** — the value was always correct; it was drawn over the bottom row of windows. Moved to the top right, opposite LEVEL/LIVES.

## Hammer sprites fixed + swing animated (2026-10-19, uncommitted)

- **Felix flipped direction when hammering.** The atlas has two complete Felix rows, one per facing (the y~230 row's strike swings right; y~326 is its mirror). The hammer frames were mapped to the opposite row from idle/walk, a mismatch that survived `ae54332` because that commit flipped all three groups together. Hammer now comes from the same row as idle/walk.
- **The swing now animates:** raise (`felix_hammer_*` frame 0) during wind-up, then the strike frame with impact sparkle (`felix_strike_*`, new; replaces the misnamed `felix_hammer_up`) while the hit lands. Frames are anchored on Felix's head (`FELIX_HEAD_CENTER_X` in `sprite_data.py`) so his body doesn't jump sideways when the wider strike frame swaps in.

## Pause (added 2026-10-19, uncommitted)

Enter / P / gamepad Start toggles pause during gameplay; the game also auto-pauses when its window loses focus (never auto-unpauses). Music and sound effects freeze in place. Drawn as a dimmed frame with "PAUSED" / "PRESS START" in the game's own bitmap font — the original has no pause graphic or pause feature at all (no sprite in the atlas, no "pause" string in the executable). Esc still quits instantly, by choice. Tests: `tests/test_game_pause.py`.

## Known issue (deferred, not blocking)

- `tests/test_building.py::test_level_progression` fails under `pytest` (but passes fine run directly via `python3 tests/test_building.py`) — a Task 6-era import-placement bug. Trivial one-line fix, queued for a cleanup pass.

## Where the detailed history lives

Every task's implementation + review + every judgment call made along the way is logged in `.superpowers/sdd/2026-06-17-fix-it-felix-pygame/progress.md` (git-ignored — it's a working ledger, not meant to ship, but it's the full record if you want it).
