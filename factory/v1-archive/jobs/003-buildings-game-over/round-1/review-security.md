VERDICT: CHANGES

## Summary
`save_high_score()` is mostly sound. It writes only to `CONFIG_PATH` (built from `__file__`), keeps unknown keys, never writes to a file it couldn't parse, serialises before it opens the file for writing, and the tests never touch the real `config.json`. But the spec's "never raises" promise is broken for two hostile config values, and that error would hit the game loop at game over.

## Findings
1. **should** `systems/score.py:52` / `systems/score.py:60`: two hostile config values still make the method raise. Python's `json` accepts `{"high_score": 1e999}` and `{"high_score": Infinity}` and reads both as `float('inf')`. Then `int(inf)` raises `OverflowError`, which is not one of `OSError`/`ValueError`/`TypeError`. A deeply nested file (for example 200k `[`) makes `json.load` raise `RecursionError`. I confirmed both with a probe. In both cases the file is left alone and `high_score` is already updated, but the exception goes up through `check_game_over()` into `start_game_loop()` and crashes the game at game over. (The out-of-scope `load_high_score()` would also fail on these values at startup, so in real play you only hit this if the file is edited mid-session. It still breaks the spec's "never raises" promise and the "huge numbers must not crash" rule.) **Fix:** add `OverflowError` and `RecursionError` to the `except` tuple. Add `1e999` (or `Infinity`) to the 15c parametrised cases.
2. **nit** `systems/score.py:58-59`: `open(CONFIG_PATH, 'w')` truncates the file before `write`. If the write then fails (disk full, I/O error), the file is left empty or partly written and the user's other config keys are lost. Serialising first already covers the common case. For a fully safe write, write to a temp file in the same directory and then `os.replace()` it onto `CONFIG_PATH`.

Checked and OK:
- No `eval`/`exec`/`pickle`/`subprocess`/`os.system`/`__import__` and no network use.
- No new dependencies.
- `check_game_over()` is the only caller of `save_high_score()`. It saves once per game, not once per frame, so no repeated disk writes.
- No new unbounded allocation. `self.buildings` only shrinks, and `spawn_incoming_missile()` builds a short list each time it runs.
- The tests redirect `CONFIG_PATH` through the fixture or their own monkeypatch before building `ScoreSystem`. The real `config.json` sha256 is the same before and after the full suite (53 passed).
