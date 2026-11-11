VERDICT: PASS

## Summary
The change is purely in-memory rendering: no file, config, network or dangerous calls, and no new dependencies. Each missile's trail is capped by `deque(maxlen=ENEMY_TRAIL_MAX_POINTS)`, and every test that builds a `MainGame` goes through the `main_game` fixture, which points `CONFIG_PATH` at `tmp_path`.

## Findings
None.

Checked:
- **File I/O:** no changes to `systems/score.py` or `config.json` handling. Nothing new reads or writes files.
- **Dangerous calls:** no `eval`, `exec`, `pickle`, `subprocess`, `os.system`, `__import__` or network use in the diff (game code or tests).
- **Dependencies:** the only new import is `collections.deque` from the standard library. No changes to requirements, pyproject or the lock file.
- **Resource exhaustion:** `entities/missile.py` sets `self.trail = deque(maxlen=...)`, so each missile keeps at most 12 samples at all times, not trimmed later in `draw()`. Destroyed missiles stop recording. `trail_segments()` builds at most 12 short-lived tuples per missile per frame. The player has no input that grows trails, and the missile count is still set by the existing spawn logic.
- **Tests:** `tests/test_enemy_exhaust_trails.py` builds `MainGame` only through the `main_game` fixture, which monkeypatches `systems.score.CONFIG_PATH` before construction. The entity and surface tests use no `MainGame`. I ran the new file and all 17 tests passed. The worktree is clean afterwards (no `config.json` change).
