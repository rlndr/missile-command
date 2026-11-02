STATUS: READY

## Round 1
**Summary** — `Building.take_impact()` takes `ceil(health_max / damage_threshold)` (34) damage per hit. The explosion-vs-building loop is gone, so only an `IncomingMissile` inside a building rect does damage. Each missile `break`s after one building, and destroyed buildings are filtered out at the end of `check_collisions()`. New `buildings_left` property and `check_game_over()`. `check_game_over()` is now the only place that switches to `STATE_GAME_OVER` and the only caller of `save_high_score()`, and it runs once per playing frame in `start_game_loop()`. `spawn_incoming_missile()` only targets standing buildings. `save_high_score()` treats a missing file as 0, keeps other keys, never touches an unparseable file, never raises (catches OSError/ValueError/TypeError) and always sets `high_score = max(high_score, score)`. The game-over screen shows a "High Score" line. The README features bullet is updated.

**Commits**
- `675afb5 003-buildings-game-over: only enemy impacts damage buildings (3 hits), filter destroyed buildings, single-save game over, hardened save_high_score, high score on game-over screen`
- `fcc7617 003-buildings-game-over: tests for impact damage, building filtering, game over and save_high_score file handling`
- `cc0b410 003-buildings-game-over: reuse impact helper for the stray-missile check`

**Acceptance criteria** (all tests in `tests/test_buildings_game_over.py`)
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|---|---|---|
| 1 | Three hits per building | `test_three_impacts_destroy_a_building` | yes |
| 2 | Impact through the game | `test_impact_through_the_game` (first half) | yes |
| 3 | Impact explosion adds no damage | `test_impact_through_the_game` (60 frames, still 66) | yes |
| 4 | Player explosions never damage buildings | `test_player_explosions_never_damage_buildings` | yes |
| 5 | One building per missile | `test_one_missile_damages_one_building` | yes |
| 6 | Destroyed buildings leave the list | `test_destroyed_buildings_leave_the_list` | yes |
| 7 | `buildings_left` counts standing only | `test_buildings_left_counts_standing_buildings` | yes |
| 8 | Spawns target standing buildings only | `test_spawns_target_standing_buildings_only` | yes |
| 9 | City redraws without destroyed building | `test_city_redraws_without_destroyed_building` | yes |
| 10 | No game over while a building stands | `test_game_over_when_last_building_falls` (first half) | yes |
| 11 | Game over when last building falls | `test_game_over_when_last_building_falls` (second half: state, file `{"high_score": 120}`, in-memory 120) | yes |
| 12 | Saved exactly once | `test_game_over_saves_exactly_once` | yes |
| 13 | No game over outside play | `test_no_game_over_outside_play` | yes |
| 14 | Real loop saves once | `test_real_loop_ends_game_and_saves_once` (fake returns quit on every call from 10 on, so it can't hang) | yes |
| 15 | `save_high_score` file handling | (a) `test_save_keeps_other_keys`; (b, c) `test_save_leaves_file_untouched[4 params]`; (d) `test_save_to_directory_does_not_raise`; (e) `test_save_zero_score_creates_no_file`. Each one checks the in-memory max | yes |
| 16 | Game-over screen draws | `test_game_over_screen_draws` | yes |
| 17 | Old tests unchanged, suite green, real config unchanged | `git diff main -- tests/test_screen_shake.py tests/test_missiles_explode.py tests/conftest.py` is empty; 53 passed; `sha256sum -c` on `config.json` before and after the run: OK | yes |
| 18 | [visual] City after a loss | Checked frame: 7 grey buildings, empty sky gap at x 30–90, no explosion rings | yes |
| 19 | [visual] Player shot over the city | Frame A: the explosion ring is centred on (220,560) over buildings[1–2]. Frame B: all 8 buildings at full health with white windows and no health bar | yes |
| 20 | [visual] Game-over screen | Checked frame: red "GAME OVER", then yellow "Final Score: 120", yellow "High Score: 120", white "Press SPACE to Restart". All centred, none overlapping | yes |

**Fail-before check:** before the game-code change, 17 of the 20 new tests failed. Three passed on the old code:
- 9: the old `take_damage(75)` also destroyed the building and `draw()` skipped it.
- 15e: a missing file with score 0 was already a no-op.
- 16: the game-over screen already drew.

All three guard behaviour that has to stay the same.

**Test notes:** the 15 tests build `ScoreSystem` while the file is missing and write the file afterwards. The un-hardened `load_high_score()` (out of scope) raises on a directory, `[1, 2]` and `"abc"`. This matches "set before the file is written".

**Size:** game code is +62/−39 lines. The test file is 318 lines, including docstrings and blank lines (about 250 non-blank). It is over the ~220 estimate because of the parametrised 15b/c cases and the shared helpers.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `53 passed in 1.98s`

## Round 2
**Summary** — `save_high_score()` now also catches `OverflowError` (from `int(inf)` when the file has `1e999` or `Infinity`) and `RecursionError` (from deeply nested JSON), so it never raises into the game loop at game over. The criterion 15c parametrised test gains three cases: `{"high_score": 1e999}`, `{"high_score": Infinity}` and 200k `[` (`deeply-nested`). For each, it checks there is no exception, the file bytes are unchanged and the in-memory high score is the max. Before the fix all three new cases failed (2× `OverflowError`, 1× `RecursionError`); now they pass.

**Commits**
- `9f00794 003-buildings-game-over: save_high_score also swallows OverflowError and RecursionError; test 1e999, Infinity and deep nesting`

**Acceptance criteria** — unchanged from Round 1, all met. Criterion 15c evidence is now `test_save_leaves_file_untouched` with 7 params. Criterion 17: the real `config.json` sha256 is the same after the full run.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `56 passed in 1.85s`

**Review responses**
- security #1 (should, OverflowError/RecursionError): fixed in `9f00794`. Both are added to the `except` tuple, with regression cases for `1e999`, `Infinity` and deep nesting.
- security #2 (nit, write a temp file then `os.replace`): not taken. The spec has the security review check that the method "only ever writes `CONFIG_PATH`", and a temp file plus rename writes a second path in the repo directory. Serialising before the truncating open already covers encoding failures. Only an I/O error in the middle of the write could leave a partial file. Worth a follow-up if a human wants atomic writes.
- ui #1 (nit, score lines 30 px apart vs restart 50 px below): no change. The spacing is exactly what the spec sets, and the reviewer agrees.
- ux #1 (nit, game over cuts in on the same frame as the final impact): not taken. A game-over delay needs a new timing constant and a state-flow change, which belongs to backlog item 4.
- ux #2 (nit, health bar only for 0.5 < health < 1.0): not taken. The building health-bar visuals are outside this job's scope.
- ux #3 (nit, SPACE on game over doesn't resume): deferred to backlog item 4, as the spec says.
