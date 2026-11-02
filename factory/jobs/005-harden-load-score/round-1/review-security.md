VERDICT: PASS

## Summary
`load_high_score()` now puts both `json.load` and `int(...)` inside one `try` with an explicit catch list `(OSError, ValueError, TypeError, OverflowError, RecursionError)`. It uses `isinstance(config, dict)` for non-objects and checks `0..HIGH_SCORE_MAX` after `int()`. It opens the file read-only (`'r'`) and only ever returns `int(...)` or `0`. No dangerous calls, no new dependencies, and tests never touch the real `config.json`.

## Checks performed
- Diff (`7bb3b12`, `b7ae8a3`): `systems/score.py` changes only `load_high_score()` (body and docstring). `CONFIG_PATH` is still built from `__file__`. No bare `except:` and no `except Exception`.
- The 4300-digit `ValueError` comes from `json.load`, and the `try` covers it. `HIGH_SCORE_MAX` is applied after `int()`, so a 4000-digit string is rejected.
- Scanned the changed files for eval/exec/pickle/subprocess/os.system/`__import__`/network. Nothing found.
- Tests: every test that builds a `ScoreSystem` or `MainGame` gets `CONFIG_PATH` from the `config_path` fixture, which monkeypatches it to `tmp_path` first (`bad_game` depends on `config_path`). The `REAL_CONFIG_KEYS` import from `tests.test_buildings_game_over` has no module-level I/O.
- Ran the full suite in the WT: 113 passed. `sha256sum config.json` was the same before and after, and `git status` is clean.
- Extra probes outside the spec's cases, all of which returned an `int` without raising:
  - `true` → 1
  - `1e300` → 0
  - `"1e999"` → 0
  - a 5000-digit string → 0
  - 100 000-deep nested objects under `high_score` → 0
  - `12.9` → 12
  - `" 7 "` → 7
  - `-0.5` → 0
  - a UTF-8 BOM file → 0

## Findings
1. **nit** `systems/score.py:35` — `open(CONFIG_PATH, 'r')` has no `encoding=`, so decoding depends on the locale. Any decode error is a `ValueError` and gets caught, so this can't crash anything. It only means a valid UTF-8 file might load as 0 on a non-UTF-8 locale. This line was already there and the spec keeps the change small, so no action is needed now. Consider `encoding="utf-8"` when the planned shared load/save helper is written.
