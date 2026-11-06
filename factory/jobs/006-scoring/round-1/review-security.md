VERDICT: PASS

## Summary
This is a game-logic change only. It adds no file or network I/O, no dangerous calls and no dependencies. `save_high_score()` is still called only from `check_game_over()`, and every new test redirects `CONFIG_PATH` to `tmp_path` before it builds a `ScoreSystem` or `MainGame`. The suite passes (132 tests), and the real `config.json` is byte-for-byte unchanged afterwards (sha256 `bbf68775...caa4c`, `git status` clean).

## Findings
None.

Checked:
- `systems/score.py`: `load_high_score()`, `save_high_score()` and `CONFIG_PATH` (built from `__file__`) are unchanged. `add_survival_time()` only does arithmetic, ignores `dt <= 0`, and only ever gets a `dt` that the loop has clamped (`clock_delay = 0.16`). A player cannot feed it a non-finite value.
- `systems/game_loop.py`: points are awarded once per missile, inside the `incoming.destroy()` branch and after the `is_destroyed` guard. No new allocation, so no new resource-exhaustion path. Removing `handle_score_updates()` takes out a dead `pygame.time.get_ticks()` path.
- Score growth: scores still go through the unchanged `HIGH_SCORE_MAX` check on load. At 10 points per intercept plus 1 per second, a player cannot realistically reach the maximum.
- No `eval`, `exec`, `pickle`, `subprocess`, `os.system`, `__import__` or network calls in the diff. No new packages.
- `tests/test_scoring.py`: the `scores` fixture and the shared `main_game` fixture both patch `systems.score.CONFIG_PATH` first. The `utils.timer.time` patch uses the `monkeypatch` fixture, so it is undone after each test. Criterion 11 reads the `config.json` under `tmp_path`, not the real one.
