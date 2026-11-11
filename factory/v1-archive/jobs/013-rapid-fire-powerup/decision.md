APPROVE

**Reason:** All 4 round-1 reviews PASS with nits only. All 16 criteria have credible evidence, 323 tests pass, and the diff stays inside scope. It also merges cleanly with current main (340 pass).

## Rationale
- **Gates:** build.md `STATUS: READY`. The code, security, ui and ux reviews all say `VERDICT: PASS`. Every finding is a **nit** (an import reflow, an unused default parameter, red matching the enemy-missile colour, no countdown). There are no **should** findings and the reviewers agree.
- **Criteria:** `tests/test_rapid_fire.py` covers criteria 1-14 one-to-one. I read the diff against the spec:
  - `rapid_fire_active()` is the only source of truth for the window and uses no wall clock. It is copied onto the base right after `game_time += dt`.
  - `cooldown_length` is set in `__init__`, `reset`, `start_cooldown` and the clamp in `set_rapid_fire`. The clamp only runs on the off-to-on switch.
  - The sound is chosen from `base.rapid_fire` before `start_cooldown()`, so each laser shot always gets the 0.1 s reload.
  - The offline look still wins in `draw_base`.
- **Visual criteria 15/16:** the builder and the UI reviewer each rendered frames. The tower is red in the window, the bar and HUD are unchanged, and the tower area at t=70.3 matches t=10 pixel for pixel. `test_game_frame_tower_red_in_window` checks the same thing on a full `draw()`.
- **Criterion 5:** the builder fires one rapid shot before the post-window step. Read literally, the 1.5 s reload from the earlier shot would still be running at that point. This reading is reasonable and matches the spec's intent.
- **Tests:** I re-ran the README command in WT: 323 passed. The `config.json` sha256 was the same before and after the run.
- **Merge:** main has moved on with 014-wave-counter. `git merge-tree` against main shows no conflicts, and the full suite on the merged tree gives 340 passed.
- **Scope:**
  - The 7 files changed match the spec's touch points.
  - `sound.py` gets one recipe line.
  - `game_loop.py` changes only the listed lines.
  - `tests/test_sound.py` has only the two allowed edits plus their import.
  - No other existing test is edited.
- **Risk / escalation triggers:**
  - No new dependency.
  - No change to `config.json` or how it is saved.
  - No files deleted.
  - `entities/base.py` and `systems/game_loop.py` only gain what the spec asks for, with no restructuring.
