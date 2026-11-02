# Fix-It Felix Jr. — Implementation Status

_Last updated: 2026-11-02_

## Running tests

```
pip install -r requirements-dev.txt        # dev-only: pins coverage
python3 -m pytest tests -q                 # tests only
python3 -m coverage run -m pytest tests -q && python3 -m coverage report
```

`.coveragerc` measures `src` with branch coverage, omits the four GUI-only modules verified by hand (`main.py`, `title_scene.py`, `cutscene_scene.py`, `game_over_scene.py`), and fails the report under 90%. Tests use SDL dummy drivers, so no window or sound device is needed. One test is an expected failure (`xfail`): a corrupt `scores.dat` is silently treated as empty (TODO in `high_score_scene.load_scores`).

## Gameplay rebuild in progress (branch `gameplay-rebuild`)

The game layer is being rebuilt from Ghidra pass 4, following `docs/superpowers/plans/2026-10-21-gameplay-rebuild.md`. **Tasks 1–11 are done and reviewed** (including the roof ending), plus the playtest fixes 8b/8c and 10b/10c. Latest commit: `f875e71`; Task 12 (the pre-refactor test safety net) and the final-review fixes are uncommitted in the working tree. The 2026-11-02 playtest passed. Run the game with `python3 src/main.py`.

### Task 10 checkpoint: passed (2026-10-30)

The checkpoint's fixes (uncommitted until the user commits):
- **Nicelander and pie position** (exe `FUN_00407190`): both share a node at the cell's middle, 2 px above the sill (`Building.nicelander_node`), with the pie drawn in front. Recorded in the pass 4 findings doc.
- **Exe cell placement** (`FUN_00405550`): the ground floor's side windows and the arched window sit 8 px higher, sills included. The arched-window step went from 9 px to 1 px; the ground-floor pane-to-door step went from 4 px to 12 px, as in the exe. The user found the step fine.
- **Panes** are drawn at `cell.x + 6`, the exe's value (was `+ 4`).
- **Drop-hazard blink** (`FUN_004073f0`): every 15 ticks, 4 visible and 3 hidden phases (105 ticks), then gone. It was every 4 ticks, so it seemed to vanish at the respawn.
- **Fix sound:** kept as is. Sound 1 plays when a swing starts at a broken window (`FUN_0040b510`), and the exe plays nothing extra when the window becomes whole.

**Checked in play (levels 3 and 5):** Felix stands on the sill ledges (stone floors, ground floor, door); obstacles rest on the ledge, block the drop down and bump a jump up from below (with a sound and a slab bounce); jumping up from an obstacle window climbs normally; Ralph's window-break, jump and drop sounds; window, arched-window and pane alignment; the Nicelander rises with the pie in front; brick floors (side and center windows in their bays); the drop-hazard is a red brick chunk in the wall gap and costs a life when walked into after landing. Earlier (2026-10-22): Nicelanders and pies (collect → 8 s blink, bricks bounce off, Ralph rages), obstacles per section, birds.

**Not seen in play:** a falling drop-hazard being harmless (the tests cover it). Open question: drop-hazards freeze during Felix's hit sequence like Ralph and the bricks (`FUN_0040e1d0`); whether the exe freezes them too isn't decoded.

**Dev shortcut (kept on purpose):** start on any level with `FELIX_START_LEVEL=5 python3 src/main.py` (`start_level_from_environment` in `src/scenes/game_scene.py`). A non-integer or a level below 1 raises at game start.

### Task 11: done, including the roof ending (2026-10-30 to 2026-11-02, commits `45db5e3`, `33cf1a5`, `1d25368`)

- Default high scores from the exe (`FUN_0040a060`): VAV 15000, DES 10000, RYS 8000, KYL 6000, CMI 4000, used when `scores.dat` is missing.
- The level end starts the next level at once; its [EXE] 180-tick pause is the next level's ready pause (`FUN_004086e0`). The roof ending is built (commit `1d25368`).
- Dead sprite entries removed (`wall_brick`, `window_*`, `shutter_*`, `niceland_sign`, `ledge`).
- **Roof ending (built; decode leads kept for reference):** `FUN_004089b0` → `FUN_004047f0`, `FUN_00404ce0` (flag `DAT_00424330`); `FUN_00402b94`, `FUN_00402cd8` (pass 4 open item 5); frames 24–29 (Felix with medal), 180–185 (medals), Ralph thrown off in 74–127. Full list: `.superpowers/sdd/2026-10-21-gameplay-rebuild/task-11-report.md`.

**Your level 1 → 2 playtest (Task 11 checkpoint), `python3 src/main.py`:**
- [x] Finishing level 1's last section went straight to level 2 (2026-10-30; the roof ending has since been added).
- [x] Level 2 opens with the usual 3 s ready pause, with the same score and lives you ended level 1 on (2026-10-30: 2300 points, ×6 after 4 deaths from 10).
- [x] With `scores.dat` moved aside, the high-score table shows VAV 15000, DES 10000, RYS 8000, KYL 6000, CMI 4000 (2026-10-30).

**Initials entry fix (2026-10-30, uncommitted, 171 tests pass):** from the exe (`FUN_00408fc0` case 8, `FUN_00407f50` input, `FUN_00408280` draw): each slot starts on "A" and the next slot goes back to "A" after a confirm (the old code started on the space, so UP gave "."); the letters are red and the current one flashes red/white (15 ticks red, 17 white). [USER] ENTER confirms as well as SPACE. Not adopted (user's choice): hold-to-repeat every 20 ticks, the 30 s TIME LEFT limit, typing inside the table row.
- [x] Get a score over 4000, then on the initials screen: the first letter flashes; DOWN gives B, UP from A gives a blank; SPACE or ENTER moves the flash to the next letter, which starts on A; the third confirm saves.

- **Later (user, 2026-10-30):** "I'd like to be given more time to update it" — revisit the initials entry (check against the exe; it has a 30 s TIME LEFT limit and hold-to-repeat that we didn't adopt).

**Next:** commit Task 12 and the final-review fixes → the refactor.

### Earlier checkpoints (all passed)
- **Task 8 (2026-10-21/22):** hit sequence (knocked down, falls, ~1 s gone, respawn, life lost at the respawn), Ralph and bricks freeze during it, last life → death animation → GAME OVER (the last head leaves the HUD at the fatal hit), section clear → Ralph climbs → scroll, level end → next level with score and lives kept.
- **Your rulings:** safer respawn (nearest window on the same floor that no brick is falling toward; ties toward the center, then left; fallback to the same window); Felix sliding off during the section scroll is fine (the exe does it too); door damage visibility left as is; brick cracks on level 2 verified by simulation.
- **Level table (exe):** levels 1–2 are 9 floors / 2 sections, levels 3–4 are 13 / 3, level 5+ is 17 / 4. Obstacles from level 3, birds from level 4, dropped objects from level 5.

**Still not built:** the intro cutscene is still the old one, to revisit separately.

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
