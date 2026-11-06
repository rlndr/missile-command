APPROVE

**Reason:** Tower, ground strip and mirrored city match the spec exactly; 4/4 PASS, 182 tests pass, config.json unchanged, no scope creep.

## Rationale
- **Gates:** build.md says `STATUS: READY`. All four round-1 reviews (code, security, ui, ux) say `VERDICT: PASS`. The only findings are two **nit**s about things the spec rules out of scope: track contrast on the ground, and clicks below the muzzle. There are no **should** findings and the reviewers agree.
- **Tests:** I re-ran the README command in WT and got `182 passed in 6.69s`. The `config.json` sha256 (`bbf68775...caa4c`) was the same before and after the run.
- **Criteria:** `tests/test_bottom_launcher.py` has one test per criterion 1-13, and criterion 6 is parametrised over the five targets. I read each test against the spec and they assert the exact values, rects and pixels the spec asks for. The UI reviewer rendered frames 15 and 16 and found them correct, which matches the builder's description.
- **Code:** All geometry comes from constants:
  - `DefensiveBase` position, size and offsets come from `LAUNCHER_*`, and the new `barrel_rect()` works from them.
  - `DefenseMissile` starts at `(LAUNCHER_X, LAUNCHER_Y)`.
  - `start_game()` works out the mirrored x values from `CITY_EDGE_MARGIN`, `BUILDING_SPACING` and the building width. It uses the same single `random.choice` per building in the same order.
  - The ground fill is drawn after the sky gradient.
  - The old tube drawing is gone. `reload_progress()` and `cooldown_bar_rects()` are untouched. `LAUNCHER_*_OFFSET` is removed with no alias and is no longer used in any code or doc outside `factory/`.
- **Existing-test edits:** The edits match the criterion 14 table. The table names `(10, ROW)` only as a game-frame pixel, but `test_cooldown_indicator.py::test_not_on_menu_screens` also moved its start-screen sample from `(10, ROW)` to `(375, ROW)`. That keeps the test checking where the bar actually is, and it does not loosen it. No tests were deleted and no assertions were weakened. `test_no_contact_detonation`'s new parked point `(400, 420)` is on the new flight path and 120 px from the target.
- **Scope:** 11 files changed: game code, constants, README, the four GAME_DESIGN sections and the allowed tests. No new dependency, no change to the config format or how it's saved, no files deleted. `game_loop.py` and `base.py` changed only in the methods the spec names.
- **Risk:** Low. It is a geometry and drawing change backed by thorough pixel and geometry tests.
