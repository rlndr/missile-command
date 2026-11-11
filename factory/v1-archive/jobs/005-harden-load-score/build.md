STATUS: READY

## Round 1
**Summary** — `ScoreSystem.load_high_score()` now wraps both the parse and the conversion in one `try` catching `(OSError, ValueError, TypeError, OverflowError, RecursionError)` (the same set as `save_high_score()`), returns 0 for any non-dict via `isinstance(config, dict)`, converts with `int(config.get("high_score", 0))`, and returns 0 if the result is outside `0..HIGH_SCORE_MAX`. It returns only `int(...)` or the literal `0`. It opens the file in `'r'` mode only. Added `HIGH_SCORE_MAX = 999_999_999` under a new `# High score` section at the end of `game/constants.py`, and replaced the docstring. New `tests/test_load_high_score.py` covers criteria 1–12. The stale "not hardened yet" sentence in the `_score_system` docstring in `tests/test_buildings_game_over.py` was reworded, and that file's test logic is unchanged.

**Commits**
- `7bb3b12 005-harden-load-score: load_high_score never raises, falls back to 0; add HIGH_SCORE_MAX`
- `b7ae8a3 005-harden-load-score: tests for malformed, out-of-range, unreadable and good config files`

**Acceptance criteria**
| # | Criterion | Evidence (test name / frame checked) | Met |
|---|-----------|--------------------------------------|-----|
| 1 | Four feature cases load as 0 | `test_feature_cases_load_as_zero[str-abc,empty-list,top-level-1e999,4301-digits]` (all 4 failed before the fix) | Yes |
| 2 | Other non-numbers load as 0 | `test_other_non_numbers_load_as_zero` (7 cases, all failed before the fix) | Yes |
| 3 | Other non-objects load as 0 | `test_other_non_objects_load_as_zero` (4 cases, all failed before the fix) | Yes |
| 4 | Unparseable files load as 0 | `test_unparseable_files_load_as_zero[not-json,empty,deep-nesting,not-utf8]` (deep-nesting and not-utf8 failed before the fix; `{not json` and empty already passed) | Yes |
| 5 | Out-of-range values load as 0 | `test_out_of_range_values_load_as_zero[negative,max-plus-one,4001-digit-int,4000-digit-str]` (all failed before the fix) | Yes |
| 6 | Good files still load | `test_good_files_still_load[250,0,max,str-120,no-key,real-keys]` (regression guard, passed before and after) | Yes |
| 7 | Missing file → 0, not created | `test_missing_file_loads_zero_and_is_not_created` (regression guard) | Yes |
| 8 | Directory path → 0 | `test_directory_path_loads_zero` (failed before the fix with IsADirectoryError) | Yes |
| 9 | Game launches with a bad file | `test_game_launches_with_bad_file` x4 (state, high_score, "High Score: 0" in COLOR_YELLOW, `draw_start_screen()`); the fixture uses `gc.collect()` before, `gc.collect()` + `pygame.quit()` after | Yes |
| 10 | Real loop runs with `[]` | `test_real_loop_runs_with_bad_file` | Yes |
| 11 | Bad file isn't overwritten after fallback | `test_bad_file_not_overwritten_after_fallback[str-abc-with-keys,empty-list]` | Yes |
| 12 | Loading is read-only | `test_loading_is_read_only[good-250,bad-empty-list]` (bytes and mtime unchanged over 3 extra loads) | Yes |
| 13 | No regressions; real config.json untouched | Full suite: 113 passed. Existing test logic is unchanged (only one docstring sentence was edited). `git status --short config.json` is empty in both the WT and the main repo | Yes |
| 14 | Start screen after a bad file | I rendered `{"high_score": "abc"}` → `MainGame()` → `draw_start_screen()` → `start_bad.png` in the scratchpad. The frame matches the normal start screen: title in white, "Defend the city!" in gray, centred "High Score: 0" in yellow, the controls, then "Press SPACE to Start". No error text and nothing cut off. The config file was unchanged afterwards | Yes |

Before the fix (constant added, `score.py` unchanged), the new file gave 30 failed, 10 passed. The 10 that passed are the good-file, missing-file, `{not json`, empty-file and good read-only regression guards.

**Tests** — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run -q --no-project --python 3.13 --with pygame --with pytest python -m pytest -q` → `113 passed in 3.83s`

**Notes**
- The new tests import `REAL_CONFIG_KEYS` via `from tests.test_buildings_game_over import REAL_CONFIG_KEYS`. This works because `conftest.py` puts the repo root on `sys.path`, which makes `tests` a namespace package. Only the constant is imported, so no extra tests are collected.
- The 200 000-deep nesting case runs before the launch and loop tests in the same session, and those tests pass, so the interpreter isn't left in a bad state.
