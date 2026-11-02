VERDICT: PASS

## Summary
The diff fixes the screen-shake crash (`math.ceil` bound passed to `random.randint`), moves the magic numbers into constants, and adds a pytest harness that keeps tests away from the real `config.json`. There are no dangerous calls, no new runtime dependencies, and no new allocation a player can trigger.

## Findings
1. **nit** `systems/score.py:24-45` — Pre-existing and not changed by this job, so it doesn't block. `load_high_score`/`save_high_score` only catch `FileNotFoundError`/`JSONDecodeError`. A hostile `config.json` (for example `[]`, `{"high_score": "abc"}`, or `{"high_score": null}`) raises `AttributeError`/`ValueError`/`TypeError` and crashes `MainGame()` at startup. `save_high_score` also opens the file with `'w'` in place, so a failure while writing truncates it. Fix in a later job: catch `(OSError, ValueError, TypeError, AttributeError)`, check that `config` is a dict, and write to a temp file in the same directory, then `os.replace`.

## Checked
- `tests/conftest.py:42` monkeypatches `systems.score.CONFIG_PATH` to `tmp_path / "config.json"` before it builds `MainGame()`. `score.py` reads the module global each time it is called, and no other module imports `CONFIG_PATH` by name, so the patch takes effect.
- `save_high_score()` is only reached from `MainGame.run()` (`systems/game_loop.py:331`), and no test calls it. I ran the suite with the SDL env vars unset (10 passed). The `config.json` sha256 was the same before and after, and `git status` was clean.
- The diff has no `eval`, `exec`, `pickle`, `subprocess`, `os.system`, `__import__`, or network calls. `conftest.py` builds the `sys.path` entry from `__file__`.
- `pytest` is a dev-only dependency and is documented in `README.md`. No requirements or pyproject changes.
- `get_shake_offset()` allocates nothing and is bounded by `shake_intensity`. That value is only ever set to the constants 5 or 8, so the player can't push it to inf or NaN.
