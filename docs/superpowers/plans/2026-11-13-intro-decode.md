# Intro animation decode — plan (Ghidra pass 5)

_2026-11-13. Approved by the user: option A (a new targeted headless Ghidra pass), then a check against footage of the original if available._

## Why

The current intro (`src/scenes/cutscene_scene.py`, steps in `src/constants/screens.py`) is a placeholder slideshow: building / Ralph sprites, invented captions ("HEY. YOU MOVED MY STUMP!", ...), invented timings. Nothing in it was decoded from the exe. Per the project rule, no assumed values: decode first, implement after.

## What pass 4 already shows (grounded)

- `FUN_00402abd` (entry, reached via the pointer table `PTR_FUN_00402dd0[param_3]`) installs `FUN_00401000` as the per-tick script callback (`DAT_00424340`), clears the background callback `DAT_00424344 = 0`, resets step `DAT_004243ec = 0` and counter `DAT_004243f0 = 0`, starts music `FUN_0040f4a0(0)`, stores `param_3` in `DAT_004243e8`.
- `FUN_00401000` is a 7-case state machine on `DAT_004243ec`. A case ends itself by setting `DAT_00424402 = 1`; the step increment happens elsewhere (unknown).
- Five sprite nodes: `DAT_00424384 / 388 / 38c / 390 / 394`. `FUN_0040ecc0(n)` is called with 0x28, 0x29, 0x2a, 0x2b, 0x56 (probably "set animation"; target node lost by the decompiler). `FUN_0040ecf0(?, node, x, y, depth)` probably places a node. Node `+0x1a` flag bits: bit0 likely visible, bit1 likely anim finished, bit3 unknown. `+0x12` likely current frame index.
- Case values: step 0 moves `b0` down to 0x78; step 1 counts `b4` past 0x17c; steps 2–3 move by 2 px/tick and every 5 ticks cycle a 3-entry table at `0x419e80` into node 384's y (shake?); step 4 waits 0x33 ticks; step 5 waits for node 38c anim end; step 6 waits 0x78 ticks, then hides the intro nodes and installs `FUN_00401470` + `thunk_FUN_00406050` (street strip) — a direct handoff into the level-start script, no scene cut.
- No text drawing in `FUN_00401000`. Our captions appear invented.
- Pass-4 findings also call `FUN_00401c78`, `FUN_00401e4c`, `FUN_00402510` "the intro script" (they damage windows while Ralph moves). So the whole script family `0x401000–0x402e00` is in scope, not just `FUN_00401000`.

## Open questions pass 5 must answer

1. Node creation: who allocates nodes 384–394, with what initial anim / frame / position / visibility (`FUN_00402780`? an init routine?).
2. Step driver: who reads `DAT_00424402` and advances `DAT_004243ec`; same tick or delayed.
3. Helper semantics from disassembly: which node each `FUN_0040ecc0` call targets (ECX/ESI), `FUN_0040ecf0` argument meanings, `+0x1a` bits, `+0x12`.
4. Anim records for 0x28, 0x29, 0x2a, 0x2b, 0x56 (table `0x419800`, 12-byte defs) and the 3 values at `0x419e80`.
5. When the intro plays: every new game, or title attract mode? Contents of the `0x402dd0` table and its caller. Meaning of `DAT_004243e8`.
6. Skip input: does the exe allow skipping (main-loop state handler)?
7. Audio: what music index 0 is (README guesses sound 7); sounds triggered from these scripts.
8. Camera offsets `0x41a298` / `0x41a248`, frame-parity `0x42427c`, and the screen-space meaning of `b0/b4`, `c0/c8`, `cc/d0`.

## Steps

1. **Pass 5 dump** — `tools/GhidraPass5Intro.java`, run by `tools/run_ghidra_pass5.sh`. Output: `docs/ghidra-output/pass5_intro.txt`. Contents: decompile + disassembly of every function in `0x401000–0x402e00` plus helpers; every read/write xref to globals `0x424340–0x424410`; disassembly context before every call to the node helpers; raw dumps of the `0x402dd0` table, `0x419e80`, and the intro anim records; strings referenced from the script functions. Nothing committed; user reviews.
2. **Decode doc** — `docs/superpowers/specs/2026-11-13-intro-decode.md`: one row per step (entry/exit condition in ticks, nodes, anims, frames, start/end positions, per-tick speeds, sounds, handoff). Every value cites an address; unresolved = [OPEN], never assumed.
3. **Tracer check** — a Python tracer (scratchpad or `tools/`) that steps the decoded state machine tick by tick and prints positions and step boundaries, to catch timing mistakes before game code.
4. **Stop for user review.** Then a separate implementation plan: likely a data-driven intro script on the existing `SpriteNode` / `graphics.animation` code, replacing the slideshow; the scene boundary decided by question 5 (lean: intro becomes a phase in `scenes/game/phases/` because it hands straight into level start).
5. Unit tests for the script logic after implementation; user verifies by eye against the original.

## Edge cases to decide later

- Handoff: intro merges into `GameScene` as a phase vs stays a scene.
- Skip: if the exe has no skip, keep ours anyway? (user call)
- Bit-flag meanings that stay unproven are named as hypotheses in the decode doc and not built on.

## Status

- [x] Plan approved (2026-11-13)
- [x] Step 1 pass 5 dump (2026-11-13) — `docs/ghidra-output/pass5_intro.txt`, 8235 lines, 39 target functions. Rerun: `tools/run_ghidra_pass5.sh` (needs `~/ghidra/ghidra_12.1.2_PUBLIC` + `/opt/homebrew/opt/openjdk@21`; the "Invalid PNG data at 00418320" analyzer error is harmless).
- [ ] Step 2 decode doc
- [ ] Step 3 tracer (deliberately not written yet: it must encode decoded values, so it follows step 2)
- [ ] Step 4 user review → implementation plan

## Ground-truth footage

User (2026-11-13) will provide screenshots from a YouTube video of the original intro, in `docs/reference/intro/` (numbered in playback order, timestamp in the filename if possible, e.g. `01_0m03s.png`). Caveat: a YouTube recording may be of the arcade cabinet, not this 2013 PC exe — confirm the source; the exe wins on any conflict. Use them to check the decode (step 2) and later the implementation by eye; they don't replace the decode.

## Resume here — first leads from the pass 5 dump (not yet decoded)

- **Step driver = `FUN_00407c00`**: reads `0x424402`, `INC [0x4243ec]` at `0x407c34`, clears the flag at `0x407c3a`. Called by pointer from `FUN_00408fc0` (the game state machine). `FUN_00407a70` also reads `0x424402` and `0x424404`; `FUN_00402de0` reads `0x424402` (called from `FUN_00407a70`).
- **Script pointer table `0x402dd0` has 4 entries**: [0] `FUN_00402abd` (installs `FUN_00401000`), [1] `FUN_00402af4` (installs `FUN_00401470`), [2] `FUN_00402b94`, [3] `FUN_00402cd8` (installs `FUN_00402510`?). Entries 4+ are code bytes, not pointers. All four reset `0x4243ec`.
- **Sub-step table `0x402478–0x4024bc`**: 18 pointers to `FUN_0040197a … FUN_0040241d`, a second script (probably dispatched from `FUN_00401470` / `FUN_004024c0`). Decode which script owns it.
- **`FUN_00402e00` (size 2544, called by `FUN_00408fc0`)** writes the camera offset `0x41a248`, so it's probably the intro/scene setup; `FUN_00402780` is shared setup (called from `FUN_00401000` step 6, `FUN_00402af4`, `FUN_00402e00`).
- **`0x419e80`** = `60, 62, 64` (the 3-entry cycle `FUN_00401000` steps 2–3 index with `% 3`; values look like frame/anim ids, not y shake — verify), followed by `318, 317, 315, 315, 317` (probably a separate table).
- **Animation table**: 82 entries (0–81); the id check stops at index 82 (id field 81). Check whether the intro's anim 0x56 (86) lies past a gap or `FUN_0040ecc0`'s argument isn't an anim index at all — read its body + call sites in the REGISTER-ARGUMENT section.
