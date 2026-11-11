VERDICT: PASS

## Summary
The round 1 should is fixed. `save_high_score()` now also catches `OverflowError` and `RecursionError`, and new regression cases cover `1e999`, `Infinity` and 200k nested `[`. Nothing else changed in round 2. The method writes only `CONFIG_PATH`, never touches a file it couldn't parse, keeps unknown keys, and can't raise into the game loop.

## Findings
1. **nit** `systems/score.py:58-59` (carried from round 1, not fixed): `open(CONFIG_PATH, 'w')` truncates before it writes, so an I/O error in the middle of the write could leave a partial file. The builder's reason for skipping it is fair: the spec says "only ever writes `CONFIG_PATH`", and the method serialises before it opens the file. Leave as a possible follow-up (temp file + `os.replace`) if atomic writes are wanted.

Round 1 item status:
- #1 (should, OverflowError/RecursionError): fixed in `9f00794`. The `except` tuple at `systems/score.py:60` now has both. `test_save_leaves_file_untouched` has the `1e999`, `Infinity` and `deeply-nested` params, and each one checks there is no exception, the file bytes are unchanged and the in-memory max is right. Other hostile values are already covered: `NaN` makes `int()` raise `ValueError`, and integers over 4300 digits raise `ValueError` from `json` on Python 3.11+. Both are caught.
- #2 (nit, atomic write): not taken, with a reason. Accepted, see above.

Re-checked:
- The full suite passes: `56 passed`. The real `config.json` sha256 is the same before and after the run, and the worktree is clean afterwards.
- The changed files have no `eval`/`exec`/`pickle`/`subprocess`/`os.system`/`__import__` and no network use. No new dependencies.
