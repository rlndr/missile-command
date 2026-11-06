VERDICT: PASS

## Summary
The change is drawing only. It adds two pure methods on `DefensiveBase`, two `pygame.draw.rect` calls per frame, five constants and a README line. It adds no file, config, network or dependency surface. The tests patch `systems.score.CONFIG_PATH` to `tmp_path` before every `MainGame()` they build, so they never write the real `config.json`.

## Findings
None.

Checked:
- **File I/O:** `systems/score.py` is not changed. The diff adds no `open()` or config read/write.
- **Dangerous calls:** None of `eval`, `exec`, `pickle`, `subprocess`, `os.system`, `__import__` or network access appears in the game code or the new test file.
- **Dependencies:** None added. The new code uses only `pygame` and the existing `from game.constants import *`.
- **Resource exhaustion:** `cooldown_bar_rects()` builds two `pygame.Rect`s per draw call and keeps none of them. No lists, pools or allocations a player can trigger. `reload_progress()` is clamped to [0, 1], so a negative or huge `cooldown_time` cannot give an oversized or negative rect width (criterion 4 parametrises -1.0 and 2x).
- **Tests:** The `start_screen_game` fixture (`tests/test_cooldown_indicator.py:56-60`) monkeypatches `CONFIG_PATH` before `MainGame()`. The other game tests use the `main_game` fixture from conftest, which does the same. The surface-draw tests use a bare `DefensiveBase()` with no `MainGame`. build.md records that the real `config.json` sha256 was the same before and after the full suite.
