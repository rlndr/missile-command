VERDICT: PASS

## Summary
`DefensiveBase.reset()` is called in place from `start_game()`, the dead `base_cooldown` attribute is gone, and the new tests cover criteria 1-10. Full suite: 147 passed.

## Findings
1. **nit** `tests/test_reset_cooldown.py` (criterion 6) — The test counts launches with a recording `DefenseMissile` subclass instead of `len(defense_missiles)`, as the spec literally says. The deviation is justified (the first missile detonates at about 1.24 s and leaves the list) and build.md documents it. No change needed.
2. **nit** `tests/test_reset_cooldown.py` (`start_screen_game` fixture) — It returns the `MainGame` class rather than a game, so the name reads slightly oddly. The `CONFIG_PATH` patch is in place before construction, so the real `config.json` is not written. No change needed.
